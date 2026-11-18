#version 450
// The shadow layer laid over the world on the shader path (multiply): where a cast shadow
// falls the ground darkens as on the classic path and takes the sky's colour, `theme.look.shade`
// (graphics plan §1.2: shade is the sky's colour, not grey). Drawn where the classic composite is,
// so everything drawn after it (roofs, walls, people) covers it as it covers the black shadow.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_layer; // premultiplied black, alpha coverage
layout(std140, set = 3, binding = 0) uniform U {
    vec4 tint; // full shade's multiplier rgb (darkening and colour); unused
};
void main() {
    float a = texture(u_layer, v_uv).a;
    o_color = vec4(mix(vec3(1.0), tint.rgb, a), 1.0);
}
