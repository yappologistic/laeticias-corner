#version 450
// The clouds at a quarter of the frame's resolution (src/render/gpu/README.md): each cloud is a
// cumulus over a point of the ground (from the world's weather cells, so they drift with the
// wind and come and go with the weather), a few round billows on a flat base, seen `altitude`
// above that point. Red is the cloud seen at this texel, green its light (0 the shaded base, 1
// the sunlit top), blue how dark it is (rain), alpha the cloud's shadow on the ground here.
layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 0) out vec4 o_color;
layout(set = 2, binding = 0) uniform sampler2D u_unused; // the drawn texture (any)

const int kClouds = 32;
const int kBillows = 5;
layout(std140, set = 3, binding = 0) uniform U {
    vec4 frame; // world px at this target's (0, 0) x, y; world px per texel; cloud count
    vec4 sun;   // ground-plane px from a cloud's point to its shadow x, y; altitude px; unused
    // Per cloud: its ground point x, y (world px), width px, seed; then its growth 0..1, how
    // dark (rain), and its parallax (world px the cloud is seen moved from over its point).
    vec4 clouds[kClouds * 2];
};

float hash(float n) {
    return fract(sin(n * 12.9898) * 43758.5453);
}

// One billow of cloud `i`: its centre from the cloud's centre (screen px, y down) and radius.
vec3 billow(float seed, float width, int k) {
    float u = float(k) / float(kBillows - 1) - 0.5; // -0.5 .. 0.5 across
    float r = width * (0.16 + 0.12 * (1.0 - abs(u) * 2.0) + 0.05 * hash(seed + float(k) * 7.1));
    float x = u * width * 0.62 + (hash(seed + float(k) * 3.3) - 0.5) * width * 0.08;
    float y = -r * 0.55 - hash(seed + float(k) * 5.9) * width * 0.06;
    return vec3(x, y, r);
}

void main() {
    vec2 w = frame.xy + gl_FragCoord.xy * frame.z; // world px of this texel (screen plane)
    int n = int(frame.w);
    float cover = 0.0;
    float light = 1.0;
    float dark = 0.0;
    float shade = 0.0;
    for (int i = 0; i < kClouds; ++i) {
        if (i >= n) break;
        vec4 a = clouds[2 * i];
        vec4 b = clouds[2 * i + 1];
        float width = a.z;
        float growth = b.x;
        // The cloud as seen: its base `altitude` above its point, moved by the parallax.
        vec2 base = a.xy - vec2(0.0, sun.z) + b.zw;
        vec2 p = w - base;
        // The shadow: the cloud's billows laid flat on the ground (2:1), offset from the sun.
        vec2 g = w - (a.xy + sun.xy * vec2(1.0, 0.5));
        if (abs(p.x) < width && p.y < width * 0.2 && p.y > -width * 0.9) {
            float d = 0.0;
            float top = 0.0;
            for (int k = 0; k < kBillows; ++k) {
                vec3 c = billow(a.w, width, k);
                float e = 1.0 - length(p - c.xy) / c.z;
                if (e > d) {
                    d = e;
                    // Light: high on the billow and toward the sun (upper left).
                    vec2 nrm = (p - c.xy) / c.z;
                    top = clamp(0.55 - nrm.y * 0.6 - nrm.x * 0.25, 0.0, 1.0);
                }
            }
            d *= step(p.y, 0.0); // the flat base
            d = clamp(d * 4.0, 0.0, 1.0) * growth;
            if (d > cover) {
                cover = d;
                light = mix(top, 0.0, smoothstep(-width * 0.12, 0.0, p.y)); // the base in shade
                dark = b.y;
            }
        }
        if (abs(g.x) < width && abs(g.y) < width * 0.6) {
            for (int k = 0; k < kBillows; ++k) {
                vec3 c = billow(a.w, width, k);
                vec2 q = vec2(g.x - c.x, (g.y - c.y * 0.3) * 2.0);
                shade = max(shade, clamp((1.0 - length(q) / c.z) * 4.0, 0.0, 1.0) * growth);
            }
        }
    }
    o_color = vec4(cover, light, dark, shade);
}
