#version 450
// The cloud deck at a quarter of the frame's resolution (src/render/gpu/README.md): the world's
// weather cells (WeatherField: where showers and clouds are) shaped by drifting fractal noise.
// Red is the deck's density where it is seen (its altitude lifts it up the screen), green the
// density of the cloud between the ground there and the sun: its shadow.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_unused; // the drawn texture (any)

const int kCells = 16;
layout(std140, set = 3, binding = 0) uniform U {
    vec4 frame;  // world px at this target's (0, 0) x, y; world px per texel; cell count
    vec4 drift;  // the wind's drift, world px x, y; feature size px; base cover 0..1
    vec4 sun;    // world px a shadow falls from its cloud, x, y; deck altitude px; unused
    vec4 cells[kCells]; // world px x, y (ground plane, y doubled), radius px, intensity
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
float fbm(vec2 p) {
    float s = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; ++i) {
        s += a * noise(p);
        p = p * 2.03 + vec2(17.1, 9.3);
        a *= 0.5;
    }
    return s;
}

// Cloud over a ground-plane point (world px, y doubled so distances are round).
float density(vec2 q) {
    float cover = drift.w;
    for (int i = 0; i < kCells; ++i) {
        if (float(i) >= frame.w) break;
        float d = length(q - cells[i].xy) / max(cells[i].z, 1.0);
        cover = max(cover, cells[i].w * (1.0 - smoothstep(0.2, 1.0, d)));
    }
    if (cover <= 0.001) return 0.0;
    // Billows: broad noise shaped by a finer one, a cell's centre filled and its edge torn.
    vec2 p = (q + drift.xy) / drift.z;
    float n = fbm(p) * 0.7 + fbm(p * 3.1 + vec2(5.2, 1.3)) * 0.3;
    // The noise decides the edge, so a cell's circle never shows.
    return smoothstep(0.45, 0.6, n * 0.9 + cover * 0.55 - 0.25);
}

void main() {
    vec2 w = frame.xy + gl_FragCoord.xy * frame.z; // world px of this texel (ground)
    vec2 q = vec2(w.x, w.y * 2.0);
    // The deck seen here stands `altitude` above the ground behind it on screen.
    float deck = density(q + vec2(0.0, sun.z * 2.0));
    float shade = density(q + sun.xy);
    o_color = vec4(deck, shade, 0.0, 1.0);
}
