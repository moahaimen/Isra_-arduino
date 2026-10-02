// M4 watcher features from a real low-resolution frame (C++ port of
// scripts/r2/frame_features.py, which documents the equations).
//
// Header-only, fixed-size arrays, no heap. `Real` is the arithmetic type of
// the background/compensated images: double reproduces the Python reference
// (checked by tests/test_r2.py through build/r2_features); float is the
// firmware variant (memory: 3 x 3072 x 4 B = 36 KB of state + 6 KB for the
// previous frame and edge map).
//
// Input per frame: L (96 x 32, 8-bit gray, row-major) and FP (17 x 16, 8-bit
// gray) thumbnails produced by the camera's binning/downsampling. No labels
// and no detector output are ever read.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstdlib>

namespace sim {

struct FrameFeatureConsts {
    static const int W = 96, H = 32, N = W * H;
    static const int CELL = 8, NCX = 12, NCY = 4;
    static const int FGW = 48, FGH = 16;
    static const int FPW = 17, FPH = 16;
};

struct FrameFeaturesOut {
    double motion, temporal, visual, edge_change, consistency, noise;  // basic front end
    double r2_motion, r2_temporal, r2_visual, r2_consistency, gain;    // gain-compensated
    double m_raw, tau_raw, v_raw, e_raw, m2_raw;
    uint64_t motion_cells;
    uint64_t fg[12];
    int fg_count;
    uint64_t fp[4];
    uint64_t sig64;
};

template <typename Real>
class FrameFeatureExtractor : public FrameFeatureConsts {
public:
    // Parameters (frame_features.py; normalisation set on the development split)
    static constexpr int DELTA_D = 15, DELTA_B = 20;
    static constexpr double DELTA_V = 12.0, K_EDGE = 2.0, CELL_FRAC = 0.10, ALPHA_B = 0.02;
    static constexpr double M_REF = 0.05, T_REF = 0.15, V_REF = 0.25, E_REF = 0.30, NOISE_REF = 16.0;
    static constexpr double GAIN_MIN = 0.5, GAIN_MAX = 2.0;

    FrameFeaturesOut step(const uint8_t* L, const uint8_t* FP) {
        FrameFeaturesOut o{};
        edge_map(L, E_);
        if (!init_) {
            for (int i = 0; i < N; ++i) {
                prev_[i] = L[i];
                prev_e_[i] = E_[i];
                bg_[i] = static_cast<Real>(L[i]);
                prev_c_[i] = static_cast<Real>(L[i]);
                bg_c_[i] = static_cast<Real>(L[i]);
            }
            init_ = true;
        }
        // ---- basic front end
        int nd = 0, nt = 0, nx = 0, nor = 0;
        for (int i = 0; i < N; ++i) {
            nd += std::abs(static_cast<int>(L[i]) - static_cast<int>(prev_[i])) > DELTA_D;
            dev_[i] = std::fabs(static_cast<Real>(L[i]) - bg_[i]);
            nt += dev_[i] > DELTA_B;
            nx += E_[i] != prev_e_[i];
            nor += E_[i] || prev_e_[i];
        }
        o.m_raw = static_cast<double>(nd) / N;
        o.tau_raw = static_cast<double>(nt) / N;
        o.e_raw = nx / (nor + 1.0);
        int vcnt = 0;
        for (int cy = 0; cy < NCY; ++cy)
            for (int cx = 0; cx < NCX; ++cx) vcnt += cell_mean(dev_, cx, cy) > DELTA_V;
        o.v_raw = static_cast<double>(vcnt) / (NCX * NCY);
        o.motion = clip01(o.m_raw / M_REF);
        o.temporal = clip01(o.tau_raw / T_REF);
        o.visual = clip01(o.v_raw / V_REF);
        o.edge_change = clip01(o.e_raw / E_REF);
        o.consistency = consistency(o.motion, o.edge_change);
        o.noise = clip01(noise_sigma(L) / NOISE_REF);
        // ---- gain-compensated front end
        double ratios[NCX * NCY];
        int nr = 0;
        for (int cy = 0; cy < NCY; ++cy)
            for (int cx = 0; cx < NCX; ++cx) {
                double sl = 0.0;
                for (int y = 0; y < CELL; ++y)
                    for (int x = 0; x < CELL; ++x) sl += L[(cy * CELL + y) * W + cx * CELL + x];
                sl /= CELL * CELL;
                const double sb = cell_mean(bg_c_, cx, cy);
                if (sl > 0.5) ratios[nr++] = sb / sl;
            }
        double g = nr ? median(ratios, nr) : 1.0;
        g = g < GAIN_MIN ? GAIN_MIN : (g > GAIN_MAX ? GAIN_MAX : g);
        o.gain = g;
        int nd2 = 0, nfg = 0;
        for (int i = 0; i < N; ++i) {
            Real v = static_cast<Real>(L[i] * g);
            lc_[i] = v < 0 ? Real(0) : (v > Real(255) ? Real(255) : v);
            dmc_[i] = std::fabs(lc_[i] - prev_c_[i]) > DELTA_D;
            nd2 += dmc_[i];
            dev_[i] = std::fabs(lc_[i] - bg_c_[i]);
            fgm_[i] = dev_[i] > DELTA_B;
            nfg += fgm_[i];
        }
        o.m2_raw = static_cast<double>(nd2) / N;
        const double t2_raw = static_cast<double>(nfg) / N;
        int v2 = 0;
        o.motion_cells = 0;
        for (int cy = 0; cy < NCY; ++cy)
            for (int cx = 0; cx < NCX; ++cx) {
                v2 += cell_mean(dev_, cx, cy) > DELTA_V;
                int cnt = 0;
                for (int y = 0; y < CELL; ++y)
                    for (int x = 0; x < CELL; ++x) cnt += dmc_[(cy * CELL + y) * W + cx * CELL + x];
                if (cnt * 10 >= CELL * CELL) o.motion_cells |= 1ULL << (cy * NCX + cx);
            }
        o.fg_count = 0;
        for (int k = 0; k < 12; ++k) o.fg[k] = 0;
        for (int y = 0; y < FGH; ++y)
            for (int x = 0; x < FGW; ++x) {
                const bool b = fgm_[(2 * y) * W + 2 * x] || fgm_[(2 * y) * W + 2 * x + 1] ||
                               fgm_[(2 * y + 1) * W + 2 * x] || fgm_[(2 * y + 1) * W + 2 * x + 1];
                const int bit = y * FGW + x;
                if (b) {
                    o.fg[bit / 64] |= 1ULL << (63 - bit % 64);
                    ++o.fg_count;
                }
            }
        o.r2_motion = clip01(o.m2_raw / M_REF);
        o.r2_temporal = clip01(t2_raw / T_REF);
        o.r2_visual = clip01(static_cast<double>(v2) / (NCX * NCY) / V_REF);
        o.r2_consistency = consistency(o.r2_motion, o.edge_change);
        // ---- state update
        for (int i = 0; i < N; ++i) {
            bg_[i] = bg_[i] + static_cast<Real>(ALPHA_B) * (static_cast<Real>(L[i]) - bg_[i]);
            bg_c_[i] = bg_c_[i] + static_cast<Real>(ALPHA_B) * (lc_[i] - bg_c_[i]);
            prev_[i] = L[i];
            prev_e_[i] = E_[i];
            prev_c_[i] = lc_[i];
        }
        dhash256(FP, o.fp);
        o.sig64 = dhash64(L);
        return o;
    }

    static void dhash256(const uint8_t* F, uint64_t out[4]) {
        for (int k = 0; k < 4; ++k) {
            uint64_t v = 0;
            for (int y = 4 * k; y < 4 * k + 4; ++y)
                for (int x = 0; x < 16; ++x) v = (v << 1) | (F[y * FPW + x + 1] > F[y * FPW + x] ? 1u : 0u);
            out[k] = v;
        }
    }

    // R3: 24 x 8 block thumbnail, integer mean of each 4 x 4 block of L.
    static void thumb192(const uint8_t* L, uint8_t* out) {
        for (int by = 0; by < 8; ++by)
            for (int bx = 0; bx < 24; ++bx) {
                int s = 0;
                for (int y = 0; y < 4; ++y)
                    for (int x = 0; x < 4; ++x) s += L[(4 * by + y) * W + 4 * bx + x];
                out[by * 24 + bx] = static_cast<uint8_t>(s / 16);
            }
    }

    static uint64_t dhash64(const uint8_t* L) {
        int s[8][9];
        for (int y = 0; y < 8; ++y)
            for (int x = 0; x < 9; ++x) {
                const int x0 = (W * x) / 9, x1 = (W * (x + 1)) / 9;
                int sum = 0, n = 0;
                for (int yy = 4 * y; yy < 4 * y + 4; ++yy)
                    for (int xx = x0; xx < x1; ++xx) {
                        sum += L[yy * W + xx];
                        ++n;
                    }
                s[y][x] = sum / n;
            }
        uint64_t v = 0;
        for (int y = 0; y < 8; ++y)
            for (int x = 0; x < 8; ++x) v = (v << 1) | (s[y][x + 1] > s[y][x] ? 1u : 0u);
        return v;
    }

private:
    bool init_ = false;
    uint8_t prev_[N];
    uint8_t prev_e_[N];
    uint8_t E_[N];
    uint8_t dmc_[N];
    uint8_t fgm_[N];
    Real bg_[N], prev_c_[N], bg_c_[N], lc_[N], dev_[N];

    static double clip01(double x) { return x < 0 ? 0.0 : (x > 1 ? 1.0 : x); }
    static double consistency(double m, double e) {
        return (m > 0.05 || e > 0.05) ? 1.0 - std::fabs(m - e) : 1.0;
    }
    template <typename T>
    static double cell_mean(const T* A, int cx, int cy) {
        double s = 0.0;
        for (int y = 0; y < CELL; ++y)
            for (int x = 0; x < CELL; ++x) s += static_cast<double>(A[(cy * CELL + y) * W + cx * CELL + x]);
        return s / (CELL * CELL);
    }
    static void edge_map(const uint8_t* L, uint8_t* E) {
        static int G[N];
        long long sum = 0;
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W; ++x) {
                int g = 0;
                if (x + 1 < W) g += std::abs(static_cast<int>(L[y * W + x + 1]) - L[y * W + x]);
                if (y + 1 < H) g += std::abs(static_cast<int>(L[(y + 1) * W + x]) - L[y * W + x]);
                G[y * W + x] = g;
                sum += g;
            }
        const long long k2 = static_cast<long long>(2 * K_EDGE);
        for (int i = 0; i < N; ++i)
            E[i] = sum > 0 && static_cast<long long>(G[i]) * N * 2 > k2 * sum;
    }
    static double noise_sigma(const uint8_t* L) {
        long long acc = 0;
        for (int y = 1; y < H - 1; ++y)
            for (int x = 1; x < W - 1; ++x) {
                auto p = [&](int dy, int dx) { return static_cast<int>(L[(y + dy) * W + x + dx]); };
                const int c = p(-1, -1) - 2 * p(-1, 0) + p(-1, 1) - 2 * p(0, -1) + 4 * p(0, 0) - 2 * p(0, 1) +
                              p(1, -1) - 2 * p(1, 0) + p(1, 1);
                acc += c < 0 ? -c : c;
            }
        return std::sqrt(M_PI / 2.0) * static_cast<double>(acc) / (6.0 * (W - 2) * (H - 2));
    }
    static double median(double* a, int n) {
        for (int i = 1; i < n; ++i) {
            const double x = a[i];
            int j = i - 1;
            while (j >= 0 && a[j] > x) {
                a[j + 1] = a[j];
                --j;
            }
            a[j + 1] = x;
        }
        return (n % 2) ? a[n / 2] : 0.5 * (a[n / 2 - 1] + a[n / 2]);
    }
};

}  // namespace sim
