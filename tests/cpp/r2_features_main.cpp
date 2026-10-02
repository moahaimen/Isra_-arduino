// Runs the C++ M4 frame-feature extractor (simulation/watcher/frame_features.h)
// on a raw frame stream and prints one CSV row per frame. Used by
// tests/test_r2.py to check the C++ port against scripts/r2/frame_features.py.
//
//   r2_features <frames.bin> <n_frames> [float]
// frames.bin: n_frames x (96*32 low-res bytes + 17*16 fingerprint bytes)
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "watcher/frame_features.h"

template <typename Real>
static int run(const std::vector<unsigned char>& buf, int n) {
    using X = sim::FrameFeatureExtractor<Real>;
    static X ex;  // large state: static storage
    const int fsz = X::N + X::FPW * X::FPH;
    std::printf("motion,temporal,visual,edge_change,consistency,noise,r2_motion,r2_temporal,r2_visual,"
                "r2_consistency,gain,motion_cells,fg_count,fg,fp,sig64,thumb192\n");
    for (int i = 0; i < n; ++i) {
        const unsigned char* p = buf.data() + static_cast<size_t>(i) * fsz;
        sim::FrameFeaturesOut o = ex.step(p, p + X::N);
        std::printf("%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%.10f,%016llx,%d,", o.motion,
                    o.temporal, o.visual, o.edge_change, o.consistency, o.noise, o.r2_motion, o.r2_temporal,
                    o.r2_visual, o.r2_consistency, o.gain, static_cast<unsigned long long>(o.motion_cells),
                    o.fg_count);
        for (int k = 0; k < 12; ++k) std::printf("%016llx", static_cast<unsigned long long>(o.fg[k]));
        std::printf(",");
        for (int k = 0; k < 4; ++k) std::printf("%016llx", static_cast<unsigned long long>(o.fp[k]));
        std::printf(",%016llx,", static_cast<unsigned long long>(o.sig64));
        uint8_t th[192];
        X::thumb192(p, th);
        for (int k = 0; k < 192; ++k) std::printf("%02x", th[k]);
        std::printf("\n");
    }
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: r2_features frames.bin n_frames [float]\n");
        return 2;
    }
    std::FILE* f = std::fopen(argv[1], "rb");
    if (!f) return 2;
    const int n = std::atoi(argv[2]);
    std::vector<unsigned char> buf(static_cast<size_t>(n) * (96 * 32 + 17 * 16));
    if (std::fread(buf.data(), 1, buf.size(), f) != buf.size()) return 2;
    std::fclose(f);
    if (argc > 3 && std::string(argv[3]) == "float") return run<float>(buf, n);
    return run<double>(buf, n);
}
