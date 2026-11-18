#version 450
// The shader path's final pass (src/render/gpu/README.md): the world target (drawn in neutral
// daylight, its cast shade already the sky's colour: shade.frag) is graded by its regions'
// `theme.look` (white balance and exposure, split toning, an S-curve and a highlight shoulder on
// lightness, midtone saturation, and at night the cool shift of low light), lit by the lamp pools
// (screened on, in dithered bands anchored to the world), hazed, and the glow layer and its bloom
// are added. Sampled sharp: whole texels stay whole, a camera between window pixels glides by one
// blended pixel at each texel edge, never by a blur.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_scene; // premultiplied
layout(set = 2, binding = 1) uniform sampler2D u_glow;  // rgb what glows; a the lamps' pools
layout(set = 2, binding = 2) uniform sampler2D u_bloom;
layout(set = 2, binding = 3) uniform sampler2D u_mean;  // the scene averaged to one texel

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
};

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
    // The exposure follows the scene toward the hour's key: pale stone held down by day, dark
    // gardens lifted at night, each place keeping its own value structure.
    vec4 m = texture(u_mean, vec2(0.5));
    float mean = luma(m.rgb / max(m.a, 1e-3)) * luma(gain.rgb);
    float adapt = clamp(key.x / max(mean, 1e-3), key.y, key.z);
    float pivot = mix(0.5, clamp(mean * adapt, 0.3, 0.62), key.w);
    vec3 c = grade(albedo, adapt, pivot);
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
    vec3 glow = g.rgb * texel.w + texture(u_bloom, v_uv).rgb * mixes.w;
    o_color = vec4(min(c, 1.0) * s.a + glow, s.a);
}
