#version 450
// Bloom, up one level (dual filter): eight taps on a ring a source texel out, weighted, added
// to the finer level below with the vertex colour's strength.
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
    vec4 sum = tap(v_uv + vec2(-h.x * 2.0, 0.0));
    sum += tap(v_uv + vec2(-h.x, h.y)) * 2.0;
    sum += tap(v_uv + vec2(0.0, h.y * 2.0));
    sum += tap(v_uv + vec2(h.x, h.y)) * 2.0;
    sum += tap(v_uv + vec2(h.x * 2.0, 0.0));
    sum += tap(v_uv + vec2(h.x, -h.y)) * 2.0;
    sum += tap(v_uv + vec2(0.0, -h.y * 2.0));
    sum += tap(v_uv + vec2(-h.x, -h.y)) * 2.0;
    o_color = sum / 12.0 * v_color.a;
}
