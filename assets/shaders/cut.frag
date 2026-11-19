#version 450
// A layer of ground cut out of what lies under it (Post::cut): the texels its picture covers
// (alpha 0.9 and over: ground, and water carrying its mark) take the target's alpha away, drawn
// with Post::cutBlend; soft edges (filtered at the coarser levels) leave it, so they still lie
// over the ground under them when the layer goes on over.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_layer; // premultiplied
void main() {
    if (texture(u_layer, v_uv).a < 0.9) discard;
    o_color = vec4(0.0, 0.0, 0.0, 1.0);
}
