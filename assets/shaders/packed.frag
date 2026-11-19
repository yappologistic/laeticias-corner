#version 450
// Sprites from the packed pages (out/reports/art-data-contract.md §1), on SDL's gpu driver: each
// texel is a word (step, ramp, normal, height, lit, snow); the colour is the ramp table's at that
// step, with the ramp swapped for the season state of the climate the sprite stands in (a row of
// the remap per climate, for the month) and snow on what catches it. On the tiers that relight,
// the step moves along the ramp by the sun of the hour against the art's baked sun (relative to
// flat ground, whose brightness is the grade's), snapped to the ramp's own steps with a dither
// anchored to the sprite's texels: hand-made pixels that never crawl. The vertex colour carries
// the tint's lightness and whether the sprite is drawn mirrored (r), the climate's row (g, in
// 1/255) and the snow cover where the sprite stands (b); alpha is the sprite's own.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_page;  // the packed page (raw words)
layout(set = 2, binding = 1) uniform sampler2D u_ramps; // step x ramp id: colour, alpha its L
layout(set = 2, binding = 2) uniform sampler2D u_remap; // ramp id x climate: the month's ramp

layout(std140, set = 3, binding = 0) uniform U {
    vec4 snow;  // the snow ramp's id; water texels' alpha (the look's water mark); unused
    vec4 sun;   // toward the sun (grid axes, unit); how much it relights (0: the art as baked)
    vec4 shape; // relight exponent on L; contact darkening; darkest ratio; brightest ratio
};

const vec3 kBaked = vec3(-0.45, 0.28, 0.85) / 1.0017; // tools/artgen render.py SUN

const mat4 kBayer = mat4(0.0, 12.0, 3.0, 15.0, 8.0, 4.0, 11.0, 7.0, 2.0, 14.0, 1.0, 13.0, 10.0,
                         6.0, 9.0, 5.0) / 16.0 + 1.0 / 32.0;

uint hashU(ivec2 p) {
    uint h = uint(p.x) * 1597334677u ^ uint(p.y) * 3812015801u;
    h = (h ^ (h >> 16u)) * 2246822519u;
    return h ^ (h >> 13u);
}

float light(vec3 n, vec3 s, bool lit) {
    return 0.42 + 0.58 * max(0.0, dot(n, s)) * (lit ? 1.0 : 0.25);
}

void main() {
    // Whole texels only (the words are not colours: never filtered).
    ivec2 size = textureSize(u_page, 0);
    ivec2 tc = clamp(ivec2(floor(v_uv * vec2(size))), ivec2(0), size - 1);
    uvec4 b = uvec4(texelFetch(u_page, tc, 0) * 255.0 + 0.5);
    uint w = b.r | (b.g << 8u) | (b.b << 16u) | (b.a << 24u);
    uint ramp = (w >> 3u) & 255u;
    if (ramp == 0u) discard; // drawn with a replacing blend: nothing here leaves what is under it
    bool mirrored = v_color.r >= 0.495;
    float tint = (v_color.r - (mirrored ? 0.5 : 0.0)) / 0.49;
    int climate = int(v_color.g * 255.0 + 0.5);
    vec4 remap = texelFetch(u_remap, ivec2(int(ramp), climate), 0);
    int now = int(remap.r * 255.0 + 0.5);
    int st = int(w & 7u);
    float cover = v_color.b;
    if (sun.w > 0.0) {
        // The normal (grid axes; a mirrored sprite swaps x and y), whether the baked sun reached
        // the texel, its height above the sprite's ground.
        vec2 nxy = (vec2(float((w >> 11u) & 31u), float((w >> 16u) & 31u)) - 15.0) / 15.0;
        if (mirrored) nxy = nxy.yx;
        vec3 n = vec3(nxy, sqrt(max(0.0, 1.0 - dot(nxy, nxy))));
        bool lit = ((w >> 30u) & 1u) != 0u;
        float h = float((w >> 21u) & 511u);
        // The sun's light against the baked sun's, each relative to flat ground's.
        float now_ = light(n, sun.xyz, lit) / (0.42 + 0.58 * sun.z);
        float baked = light(n, kBaked, lit) / (0.42 + 0.58 * kBaked.z);
        float ratio = mix(1.0, now_ / baked, sun.w);
        // Contact: the feet of walls and what faces down (under eaves) a little darker.
        float upright = 1.0 - smoothstep(0.3, 0.6, n.z);
        ratio *= 1.0 - shape.y * sun.w * upright * (1.0 - smoothstep(0.0, 6.0, h));
        ratio *= 1.0 - shape.y * sun.w * step(nxy.x + nxy.y, -0.7) * step(n.z, 0.3);
        // Shade deepens freely; light lifts gently and little (a ramp's top steps hold its
        // texture: lifted far, a sunlit wall would go flat and pale).
        ratio = clamp(ratio, 1.0 / shape.z, shape.w);
        float k = ratio < 1.0 ? pow(ratio, shape.x) : pow(ratio, shape.x * 0.5);
        // Along the ramp to the step whose lightness is nearest, dithered between the two.
        float target = texelFetch(u_ramps, ivec2(st, now), 0).a * k;
        int lo = 0;
        int last = 0;
        for (int k = 0; k < 8; ++k) {
            float l = texelFetch(u_ramps, ivec2(k, now), 0).a;
            if (l <= 0.0) break;
            last = k;
            if (l <= target) lo = k;
        }
        float l0 = texelFetch(u_ramps, ivec2(lo, now), 0).a;
        float l1 = texelFetch(u_ramps, ivec2(min(lo + 1, last), now), 0).a;
        float f = l1 > l0 ? clamp((target - l0) / (l1 - l0), 0.0, 1.0) : 0.0;
        if (target < texelFetch(u_ramps, ivec2(0, now), 0).a) f = 0.0;
        ivec2 bc = tc & 3;
        st = (lo < last && f > kBayer[bc.x][bc.y]) ? lo + 1 : lo;
        // Snow lingers where the sun does not reach (facing away, or in the art's own shade).
        if (dot(n, sun.xyz) < 0.15 || !lit) cover = sqrt(cover);
    }
    vec3 c = texelFetch(u_ramps, ivec2(st, now), 0).rgb;
    // Snow on what catches it, as much as lies there: a stable share of the sprite's own texels
    // (so it builds and thaws grain by grain, and a cached picture keeps its grains).
    if ((w >> 31u) != 0u && cover > 0.0 && float(hashU(tc) & 1023u) / 1024.0 < cover) {
        float l = dot(c, vec3(0.299, 0.587, 0.114));
        int s = clamp(int(l * 4.0) + 1, 1, 3); // the cool steps: the home art's snow is these
        // A little of what is under it shows through (joints, tufts): snow, not paint.
        c = mix(texelFetch(u_ramps, ivec2(s, int(snow.x)), 0).rgb, c, 0.15);
    }
    // Water texels carry the look's water mark in their alpha (opaque sprites only: one fading
    // is drawn blended and keeps its own alpha).
    float a = v_color.a >= 1.0 && remap.g > 0.5 ? snow.y : v_color.a;
    o_color = vec4(c * tint, a);
}
