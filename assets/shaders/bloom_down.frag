#version 450
// Bloom, down one level (dual filter): the centre and four diagonal taps half a source texel
// out, read with linear filtering, so each halving blurs as it shrinks.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_src;
layout(std140, set = 3, binding = 0) uniform U {
    vec4 texel; // half a source texel in uv x, y; the source's used uv extent x, y
};
vec4 tap(vec2 uv) {
    return texture(u_src, min(uv, texel.zw));
}
void main() {
    vec2 h = texel.xy;
    vec4 sum = tap(v_uv) * 4.0;
    sum += tap(v_uv - h) + tap(v_uv + h);
    sum += tap(v_uv + vec2(h.x, -h.y)) + tap(v_uv + vec2(-h.x, h.y));
    o_color = sum / 8.0;
}
