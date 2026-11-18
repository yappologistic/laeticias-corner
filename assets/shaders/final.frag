#version 450
// The shader path's final pass (src/render/gpu/README.md): the world target, drawn in neutral
// daylight, takes the sky's colour where the shadow layer shades it, is graded by its regions' `theme.look` (white balance and exposure, split toning, an
// S-curve and a highlight shoulder on lightness, midtone saturation, and at night the cool shift
// of low light), lit by the lamp pools (albedo times light plus a warm share, in dithered bands
// anchored to the world), hazed, and the glow layer and its bloom are added. Sampled sharp: whole texels stay whole, a camera between window
// pixels glides by one blended pixel at each texel edge, never by a blur.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_scene; // premultiplied
layout(set = 2, binding = 1) uniform sampler2D u_light;
layout(set = 2, binding = 2) uniform sampler2D u_glow;
layout(set = 2, binding = 3) uniform sampler2D u_bloom;
layout(set = 2, binding = 4) uniform sampler2D u_shadow; // the cast shadows' coverage (alpha)

layout(std140, set = 3, binding = 0) uniform U {
    vec4 gain;   // white balance times exposure; tint amount
    vec4 shadow; // shadow tint - 0.5; contrast
    vec4 high;   // highlight tint - 0.5; saturation
    vec4 haze;   // colour; strength
    vec4 mixes;  // shoulder; pool gain; pool warm share; bloom gain
    vec4 texel;  // target texture w, h; window px per target px; glow core gain
    vec4 world;  // art px at target (0, 0) x, y; target px per art px; pool bands
    vec4 night;  // the low light's tint (luma 1); how far night shifts toward it
    vec4 shade;  // the sky's colour in shade (luma 1); how far shadow coverage takes it
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

vec3 grade(vec3 c) {
    c *= gain.rgb;
    float l = luma(c);
    float ws = 1.0 - smoothstep(0.0, 0.55, l);
    float wh = smoothstep(0.45, 1.0, l);
    c = clamp(c + (ws * shadow.rgb + wh * high.rgb) * gain.a, 0.0, 1.0);
    // The curve on lightness alone: per channel it would saturate warm earth into orange.
    l = luma(c);
    float k = l + shadow.a * (l - 0.5) * l * (1.0 - l) * 4.0;
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
    albedo *= mix(vec3(1.0), shade.rgb, texture(u_shadow, uv).a * shade.a);
    vec3 c = grade(albedo);
    // Lamp light in a few bands with a dithered edge, the cell anchored to world art pixels so
    // nothing crawls while the camera pans.
    vec3 light = texture(u_light, uv).rgb;
    ivec2 cell = ivec2(mod(floor(uv * texel.xy / world.z + world.xy), 4.0));
    light = floor(light * world.w + kBayer[cell.x][cell.y]) / world.w;
    c += light * (albedo * mixes.y + luma(albedo) * mixes.z);
    c = mix(c, haze.rgb, haze.a);
    vec3 glow = texture(u_glow, uv).rgb * texel.w + texture(u_bloom, v_uv).rgb * mixes.w;
    o_color = vec4(min(c, 1.0) * s.a + glow, s.a);
}
