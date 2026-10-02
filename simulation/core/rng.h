// Deterministic, platform-independent pseudo-random number generation.
//
// The C++ standard library distributions (std::normal_distribution, ...) are
// implementation-defined, so the same seed can give different numbers with a
// different standard library. Every distribution used by the simulator is
// therefore implemented here on top of xoshiro256** seeded through SplitMix64.
//
// Two kinds of streams are used:
//   * sequential streams (Rng(seed)) for workload generation, and
//   * keyed streams (Rng::keyed(seed, tag, id)) for per-event draws such as
//     detector confidence or RPC jitter. A keyed stream depends only on
//     (seed, tag, id), so the same event gets the same detector outcome in
//     every operating mode that processes it (common random numbers), which
//     is what makes paired comparisons between modes fair.
#pragma once

#include <cmath>
#include <cstdint>

namespace sim {

inline uint64_t splitmix64(uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

inline uint64_t hash_combine(uint64_t a, uint64_t b) {
    return splitmix64(a ^ (splitmix64(b) + 0x632BE59BD9B4E019ULL + (a << 6) + (a >> 2)));
}

// FNV-1a 64-bit hash of a C string (stable across platforms).
inline uint64_t hash_str(const char* s) {
    uint64_t h = 0xcbf29ce484222325ULL;
    while (*s) {
        h ^= static_cast<unsigned char>(*s++);
        h *= 0x100000001b3ULL;
    }
    return h;
}

class Rng {
public:
    explicit Rng(uint64_t seed) {
        uint64_t x = seed;
        for (int i = 0; i < 4; ++i) {
            x = splitmix64(x + static_cast<uint64_t>(i));
            s_[i] = x;
        }
    }

    static Rng keyed(uint64_t seed, const char* tag, uint64_t id) {
        return Rng(hash_combine(hash_combine(seed, hash_str(tag)), id));
    }

    uint64_t next_u64() {
        const uint64_t result = rotl(s_[1] * 5, 7) * 9;
        const uint64_t t = s_[1] << 17;
        s_[2] ^= s_[0];
        s_[3] ^= s_[1];
        s_[1] ^= s_[2];
        s_[0] ^= s_[3];
        s_[2] ^= t;
        s_[3] = rotl(s_[3], 45);
        return result;
    }

    // Uniform in [0, 1).
    double uniform() { return static_cast<double>(next_u64() >> 11) * 0x1.0p-53; }
    double uniform(double a, double b) { return a + (b - a) * uniform(); }
    // Uniform integer in [lo, hi].
    int64_t uniform_int(int64_t lo, int64_t hi) {
        const uint64_t span = static_cast<uint64_t>(hi - lo) + 1;
        return lo + static_cast<int64_t>(next_u64() % span);
    }
    bool bernoulli(double p) { return uniform() < p; }

    // Box-Muller; both uniforms are always consumed so the stream position
    // does not depend on cached state.
    double normal(double mean, double sd) {
        double u1 = uniform();
        const double u2 = uniform();
        if (u1 < 1e-300) u1 = 1e-300;
        const double z = std::sqrt(-2.0 * std::log(u1)) * std::cos(6.283185307179586 * u2);
        return mean + sd * z;
    }
    double exponential(double rate) {
        double u = uniform();
        if (u < 1e-300) u = 1e-300;
        return -std::log(u) / rate;
    }
    // Log-normal parameterised by its median and the sigma of log(X).
    double lognormal_median(double median, double sigma) {
        return median * std::exp(normal(0.0, sigma));
    }
    // Knuth's algorithm; adequate for the small means used here.
    int poisson(double lambda) {
        const double l = std::exp(-lambda);
        int k = 0;
        double p = 1.0;
        do {
            ++k;
            p *= uniform();
        } while (p > l && k < 1000);
        return k - 1;
    }

private:
    static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
    uint64_t s_[4];
};

inline double clamp01(double x) { return x < 0.0 ? 0.0 : (x > 1.0 ? 1.0 : x); }
inline double sigmoid(double z) { return 1.0 / (1.0 + std::exp(-z)); }

}  // namespace sim
