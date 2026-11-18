#version 450
// The shader path's final pass (src/render/gpu/README.md): the world target (drawn in neutral
// daylight, its cast shade already the sky's colour: shade.frag) is graded by its regions'
// `theme.look` (white balance and exposure, split toning, an S-curve and a highlight shoulder on
// lightness, midtone saturation, and at night the cool shift of low light), lit by the lamp pools
// (screened on, in dithered bands anchored to the world), hazed, and the glow layer and its bloom
// are added. Water (where the ground cells marked it: alpha just under 1) is drawn in layers from
// the tile water field: depth bands, a flowing ripple, the shore line and foam, glints, rain rings,
// the sky and (High) what stands at its edge mirrored; the cloud deck's shadows and the deck
// itself come from a quarter-resolution pass. Sampled sharp: whole texels stay whole, a camera
// between window pixels glides by one blended pixel at each texel edge, never by a blur.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_scene; // premultiplied
layout(set = 2, binding = 1) uniform sampler2D u_glow;  // rgb what glows; a the lamps' pools
layout(set = 2, binding = 2) uniform sampler2D u_bloom;
layout(set = 2, binding = 3) uniform sampler2D u_mean;  // the scene averaged to one texel
layout(set = 2, binding = 4) uniform sampler2D u_water; // per tile: shore distance, flow, flags
layout(set = 2, binding = 5) uniform sampler2D u_cloud; // r the deck seen, g its shadow

layout(std140, set = 3, binding = 0) uniform U {
    vec4 gain;   // white balance times exposure; tint amount
    vec4 shadow; // shadow tint - 0.5; contrast
    vec4 high;   // highlight tint - 0.5; saturation
    vec4 haze;   // colour; strength
    vec4 mixes;  // shoulder; pool gain; pool warm share; bloom gain
    vec4 texel;  // target texture w, h; window px per target px; glow core gain
    vec4 world;  // art px at target (0, 0) x, y; target px per art px; pool bands
    vec4 night;  // the low light's tint (luma 1); how far night shifts toward it
    vec4 key;    // the hour's key (mean luma aimed at); least, most exposure; daylight 0..1
    vec4 pool;   // the pools' scale (stored with headroom); the lamps' colour
    vec4 guard;  // most a pixel's saturation may grow by day (times the art's); grid w, h; 1 / the
                 // tiles beyond it over which the sea hazes away
    vec4 water;  // the water field's first tile x, y; 1 / its size x, y
    vec4 tiles;  // half a tile's width, height (world px); a level's height; seconds (wrapped)
    vec4 shallow; // shallow water's colour; bands (0: no layered water)
    vec4 deep;   // deep water's colour; 1: mirror what stands at the water's edge
    vec4 skyw;   // the sky's colour in the water; how much of it
    vec4 cloud;  // the deck's opacity at this zoom; its shadows' strength; rain 0..1; glints
    vec4 deck;   // the deck's colour; unused
};

uint hashU(ivec2 p) {
    uint h = uint(p.x) * 1597334677u ^ uint(p.y) * 3812015801u;
    h = (h ^ (h >> 16u)) * 2246822519u;
    return h ^ (h >> 13u);
}
float hash(vec2 p) {
    return float(hashU(ivec2(floor(p)))) * (1.0 / 4294967295.0);
}
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + 1.0), u.x),
               u.y);
}
float fbm2(vec2 p) {
    return 0.65 * noise(p) + 0.35 * noise(p * 2.03 + vec2(17.1, 9.3));
}
bool isWater(float a) {
    return a > 0.5 && a < 0.995;
}
int flagsAt(vec2 tile) {
    ivec2 i = clamp(ivec2(floor(tile - water.xy)), ivec2(0), ivec2(textureSize(u_water, 0)) - 1);
    return int(texelFetch(u_water, i, 0).a * 255.0 + 0.5);
}

const mat4 kBayer = mat4(0.0, 12.0, 3.0, 15.0, 8.0, 4.0, 11.0, 7.0, 2.0, 14.0, 1.0, 13.0, 10.0,
                         6.0, 9.0, 5.0) / 16.0 + 1.0 / 32.0;

float luma(vec3 c) {
    return dot(c, vec3(0.299, 0.587, 0.114));
}

vec2 sharp(vec2 uv) {
    vec2 p = uv * texel.xy - 0.5;
    vec2 i = floor(p);
    vec2 f = clamp((p - i - 0.5) * max(texel.z, 1.0) + 0.5, 0.0, 1.0);
    return (i + f + 0.5) / texel.xy;
}

vec3 grade(vec3 c, float adapt, float pivot) {
    c *= gain.rgb * adapt;
    float l = luma(c);
    float ws = 1.0 - smoothstep(0.0, 0.55, l);
    float wh = smoothstep(0.45, 1.0, l);
    c = clamp(c + (ws * shadow.rgb + wh * high.rgb) * gain.a, 0.0, 1.0);
    // The curve on lightness alone (per channel it would saturate warm earth into orange), by
    // day about the scene's own middle (about mid grey it bleaches pale stone).
    l = luma(c);
    float k = l + shadow.a * (l - pivot) * l * (1.0 - l) * 4.0;
    k = k > 0.8 ? 0.8 + (k - 0.8) * (1.0 - mixes.x) : k;
    c *= k / max(l, 1e-4);
    float s = 1.0 + (high.a - 1.0) * (1.0 - abs(2.0 * k - 1.0));
    c = k + (c - k) * s;
    c = mix(c, luma(c) * night.rgb, night.a);
    return clamp(c, 0.0, 1.0);
}

void main() {
    vec2 uv = sharp(v_uv);
    vec4 s = texture(u_scene, uv);
    vec3 albedo = s.a > 0.0 ? s.rgb / s.a : vec3(0.0);
    vec2 px = uv * texel.xy;            // scene target px
    vec2 w = world.xy + px / world.z;   // world px
    ivec2 bc = ivec2(mod(floor(w), 4.0));
    float dither = kBayer[bc.x][bc.y];
    float t = tiles.w;
    bool wet = shallow.w > 0.0 && isWater(s.a);
    float band = 0.0;
    float rip = 0.5;
    vec2 q = vec2(w.x, 2.0 * w.y); // the ground plane, round
    vec3 white = vec3(1.0);
    float shoreLine = 0.0;
    float foam = 0.0;
    float far = 0.0;
    float reflected = 0.0;
    if (wet) {
        // The tile under this pixel on the water's own level (the field holds the level).
        vec2 t0 = 0.5 * vec2(w.y / tiles.y + w.x / tiles.x, w.y / tiles.y - w.x / tiles.x);
        int flags = flagsAt(t0);
        float lift = float(flags & 15) * tiles.z;
        vec2 tt = 0.5 * vec2((w.y + lift) / tiles.y + w.x / tiles.x,
                             (w.y + lift) / tiles.y - w.x / tiles.x);
        vec4 f = texture(u_water, (tt - water.xy) * water.zw);
        flags = flagsAt(tt);
        bool channel = (flags & 64) != 0;
        // Beyond the grid the art's haze takes over with distance.
        vec2 out2 = max(max(-tt, tt - guard.yz), 0.0);
        far = smoothstep(0.0, 1.0, max(out2.x, out2.y) * guard.w);
        float shore = f.r * 10.0 - 1.0; // tiles from the shore
        vec2 flow = f.gb * 2.0 - 1.0;   // tiles per second
        vec2 fq = flow.x * vec2(tiles.x, 2.0 * tiles.y) + flow.y * vec2(-tiles.x, 2.0 * tiles.y);
        // A ripple advected along the flow in two phases half a cycle apart, cross-faded: it
        // moves forever and never stretches; still water stirs slowly.
        float ph0 = fract(t * 0.25);
        float ph1 = fract(t * 0.25 + 0.5);
        vec2 stir = vec2(t * 3.0, t * 1.7);
        float r0 = fbm2((q - fq * ph0 * 4.0 + stir) * vec2(0.045, 0.11));
        float r1 = fbm2((q - fq * ph1 * 4.0 + stir + 31.7) * vec2(0.045, 0.11));
        rip = mix(r0, r1, abs(ph0 * 2.0 - 1.0));
        // A few hard depth bands from the shore, their edges wobbling slowly; channels are clear
        // and dark (a narrow channel all shallow and foamy read milky).
        float wob = (noise(q * 0.018 + vec2(t * 0.05, -t * 0.03)) - 0.5) * 0.7;
        float depth = channel ? 0.75 : clamp((shore + wob) / 2.2, 0.0, 1.0);
        band = min(floor(depth * shallow.w + dither * 0.35), shallow.w - 1.0) / max(shallow.w - 1.0, 1.0);
        vec3 body = mix(mix(shallow.rgb, deep.rgb, band), albedo, 0.3);
        body *= 0.93 + 0.14 * step(0.64, rip); // crests: faint lighter dashes in whole pixels
        // Rain rings, growing and fading.
        if (cloud.z > 0.01) {
            vec2 rc = floor(q / 18.0);
            float rp = fract(t * 0.8 + hash(rc) * 5.0);
            vec2 centre = (rc + 0.25 + 0.5 * vec2(hash(rc + 1.3), hash(rc + 2.9))) * 18.0;
            float ring = abs(length(q - centre) - rp * 7.0);
            if (ring < 0.9 && rp < 0.85 && hash(rc + floor(t * 0.8 + hash(rc) * 5.0)) < cloud.z)
                body = mix(body, white, 0.4 * (1.0 - rp));
        }
        // What stands at the water's edge, mirrored (2:1: a point h px above its foot reflects
        // h px below it), found by walking up the screen to the edge; rippled in whole pixels.
        if (deep.w > 0.5) {
            float ox = floor((rip - 0.5) * 3.0 + 0.5);
            float stepPx = max(world.z, 1.0) * 2.0;
            float e = -1.0;
            for (int i = 1; i <= 40; ++i) {
                vec2 p = px + vec2(0.0, -stepPx * float(i));
                if (p.y < 0.0) break;
                float a = texture(u_scene, p / texel.xy).a;
                if (a >= 0.995) {
                    e = p.y;
                    break;
                }
            }
            if (e >= 0.0) {
                vec2 m = vec2(px.x + ox, 2.0 * e - px.y);
                vec4 r = texture(u_scene, m / texel.xy);
                // Darker than what it mirrors and tinted by the water; it fades with distance
                // from the edge (the ripples break it up).
                float reach = 1.0 - smoothstep(8.0, 44.0, (px.y - e) / max(world.z, 1e-3));
                if (m.y >= 0.0 && r.a >= 0.995) {
                    reflected = 0.5 * reach;
                    body = mix(body, r.rgb * vec3(0.62, 0.70, 0.78) + body * 0.2, reflected);
                }
            }
        }
        albedo = mix(body, albedo, far);
        // The bright shore line where water meets what stands in it, and foam that breathes.
        for (int i = 0; i < 4; ++i) {
            vec2 o = vec2(i == 0 ? 1.0 : (i == 1 ? -1.0 : 0.0), i == 2 ? 1.0 : (i == 3 ? -1.0 : 0.0));
            if (texture(u_scene, (px + o * 2.0 * max(world.z, 1.0)) / texel.xy).a >= 0.995)
                shoreLine = 1.0;
        }
        float breathe = 0.18 + 0.12 * sin(t * 0.9 + q.x * 0.03 + q.y * 0.02);
        foam = channel ? 0.0
                       : step(shore + wob * 0.3, breathe) *
                             step(0.45, noise(q * 0.09 + vec2(t * 0.6, t * 0.2)));
    }
    // The exposure follows the scene toward the hour's key: pale stone held down by day, dark
    // gardens lifted at night, each place keeping its own value structure.
    vec4 m = texture(u_mean, vec2(0.5));
    float mean = luma(m.rgb / max(m.a, 1e-3)) * luma(gain.rgb);
    float adapt = clamp(key.x / max(mean, 1e-3), key.y, key.z);
    float pivot = mix(0.5, clamp(mean * adapt, 0.3, 0.62), key.w);
    // Cloud shadows: the sun's share taken, cooler (a cloud's shadow lowers only the sun).
    vec4 cl = texture(u_cloud, v_uv);
    // In dithered steps, as the deck is drawn (pixel art, no airbrushed smudge).
    float shadowLevel = floor(cl.g * 4.0 + dither * 0.999) / 4.0;
    albedo *= 1.0 - shadowLevel * cloud.y * vec3(1.0, 0.94, 0.82);
    vec3 c = grade(albedo, adapt, pivot);
    // Richer, never garish: by day no pixel's saturation grows past a share over the art's own.
    float hiIn = max(albedo.r, max(albedo.g, albedo.b));
    float satIn = hiIn > 0.0 ? (hiIn - min(albedo.r, min(albedo.g, albedo.b))) / hiIn : 0.0;
    float hiOut = max(c.r, max(c.g, c.b));
    float satOut = hiOut > 0.0 ? (hiOut - min(c.r, min(c.g, c.b))) / hiOut : 0.0;
    float cap = min(satIn * guard.x + 0.02, 1.0);
    if (satOut > cap) {
        float l = luma(c);
        c = mix(c, l + (c - l) * cap / satOut, key.w);
    }
    if (wet) {
        // The sky in the water, deeper water showing more of it; the shore line and foam; glints
        // on the sun's side, few and short.
        c = mix(c, skyw.rgb,
                skyw.a * (0.3 + 0.45 * band) * (1.0 - cl.g * 0.5) * (1.0 - far) * (1.0 - reflected));
        float lum = max(luma(c) * 1.6, 0.25);
        c = mix(c, white * lum, shoreLine * 0.75);
        c = mix(c, white * lum, foam * 0.5);
        vec2 cq = q - vec2(t * 4.0, t * 2.0);
        vec2 cellq = floor(cq / vec2(22.0, 14.0));
        float hc = hash(cellq);
        float life = fract(t * 0.5 + hc * 7.0);
        vec2 spot = (cellq + vec2(hash(cellq + 3.1), hash(cellq + 7.7))) * vec2(22.0, 14.0);
        vec2 dq = cq - spot;
        float len = life < 0.08 ? 1.5 : (life < 0.16 ? 3.5 : 1.5);
        float glint = step(abs(dq.x), len) * step(abs(dq.y), 0.9) * step(life, 0.2) *
                      step(0.74, hc) * step(0.2, band);
        c = mix(c, vec3(1.0, 0.98, 0.9), glint * cloud.w * (1.0 - cl.g));
    }
    // Lamp light in a few bands with a dithered edge, the cell anchored to world art pixels so
    // nothing crawls while the camera pans.
    vec4 g = texture(u_glow, uv);
    ivec2 cell = ivec2(mod(floor(uv * texel.xy / world.z + world.xy), 4.0));
    vec3 light = pool.yzw * (floor(g.a * pool.x * world.w + kBayer[cell.x][cell.y]) / world.w);
    // Screened on, so a white wall beside a flame rolls off to warm white instead of clipping
    // into a flat block.
    vec3 lit = clamp(light * (albedo * mixes.y + luma(albedo) * mixes.z), 0.0, 1.0);
    c = 1.0 - (1.0 - clamp(c, 0.0, 1.0)) * (1.0 - lit);
    // Haze leans the lit toward the air and leaves the darks dark (never milky).
    c = mix(c, haze.rgb, haze.a * (0.25 + 0.75 * luma(c)));
    // The deck over everything, in three soft steps dithered at their edges (pixel-art cloud).
    float level = floor(cl.r * 3.0 + dither * 0.999) / 3.0;
    c = mix(c, deck.rgb, level * cloud.x);
    vec3 glow = g.rgb * texel.w + texture(u_bloom, v_uv).rgb * mixes.w;
    float alpha = wet ? 1.0 : s.a;
    o_color = vec4(min(c, 1.0) * alpha + glow, alpha);
}
