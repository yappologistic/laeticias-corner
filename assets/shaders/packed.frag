#version 450
// Sprites from the packed pages (out/reports/art-data-contract.md §1), on SDL's gpu driver: each
// texel is a word (step, ramp, normal, height, lit, snow); the colour is the ramp table's at that
// step, with the ramp swapped for the season state of the climate the sprite stands in (a row of
// the remap per climate, for the month) and snow on what catches it. The vertex colour carries,
// for these sprites, the tint's lightness (r), the climate's row (g, in 1/255) and the snow
// cover where the sprite stands (b); alpha is the sprite's own.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_page;  // the packed page (raw words)
layout(set = 2, binding = 1) uniform sampler2D u_ramps; // step x ramp id: the ramp table
layout(set = 2, binding = 2) uniform sampler2D u_remap; // ramp id x climate: the month's ramp

layout(std140, set = 3, binding = 0) uniform U {
    vec4 snow; // the snow ramp's id; water texels' alpha (the look's water mark); unused
};

uint hashU(ivec2 p) {
    uint h = uint(p.x) * 1597334677u ^ uint(p.y) * 3812015801u;
    h = (h ^ (h >> 16u)) * 2246822519u;
    return h ^ (h >> 13u);
}

void main() {
    // Whole texels only (the words are not colours: never filtered).
    ivec2 size = textureSize(u_page, 0);
    ivec2 tc = clamp(ivec2(floor(v_uv * vec2(size))), ivec2(0), size - 1);
    uvec4 b = uvec4(texelFetch(u_page, tc, 0) * 255.0 + 0.5);
    uint w = b.r | (b.g << 8u) | (b.b << 16u) | (b.a << 24u);
    uint ramp = (w >> 3u) & 255u;
    if (ramp == 0u) discard; // drawn with a replacing blend: nothing here leaves what is under it
    int climate = int(v_color.g * 255.0 + 0.5);
    vec4 remap = texelFetch(u_remap, ivec2(int(ramp), climate), 0);
    int now = int(remap.r * 255.0 + 0.5);
    vec3 c = texelFetch(u_ramps, ivec2(int(w & 7u), now), 0).rgb;
    // Snow on what catches it, as much as lies there: a stable share of the sprite's own texels
    // (so it builds and thaws grain by grain, and a cached picture keeps its grains).
    if ((w >> 31u) != 0u && v_color.b > 0.0 &&
        float(hashU(tc) & 1023u) / 1024.0 < v_color.b) {
        float l = dot(c, vec3(0.299, 0.587, 0.114));
        int s = clamp(int(l * 4.0) + 1, 1, 3); // the cool steps: the home art's snow is these
        // A little of what is under it shows through (joints, tufts): snow, not paint.
        c = mix(texelFetch(u_ramps, ivec2(s, int(snow.x)), 0).rgb, c, 0.15);
    }
    // Water texels carry the look's water mark in their alpha (opaque sprites only: one fading
    // is drawn blended and keeps its own alpha).
    float a = v_color.a >= 1.0 && remap.g > 0.5 ? snow.y : v_color.a;
    o_color = vec4(c * v_color.r, a);
}
