#version 450
// A layer's own alpha stamped onto the target where the layer covers it (Post::stamp): drawn
// after the layer went on over (premultiplied), with Post::stampBlend, the texels its picture
// covers (alpha 0.9 and over: ground, and water carrying its mark) set the target's alpha to
// the layer's, colour kept; soft edges (filtered at the coarser levels) keep what the blend made.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_layer; // premultiplied
void main() {
    float a = texture(u_layer, v_uv).a;
    if (a < 0.9) discard;
    o_color = vec4(0.0, 0.0, 0.0, a);
}
