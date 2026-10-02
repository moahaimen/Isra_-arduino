#include "detector/detector.h"

#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "core/rng.h"

namespace sim {

namespace {

double logit(double p) {
    if (p < 1e-9) p = 1e-9;
    if (p > 1.0 - 1e-9) p = 1.0 - 1e-9;
    return std::log(p / (1.0 - p));
}

int other_class(Rng& r, int true_cls) {
    // Uniform over the classes that are not the true one.
    int c = static_cast<int>(r.uniform_int(1, kNumObjectClasses - 1));
    if (true_cls >= 1 && c >= true_cls) ++c;
    if (c > kNumObjectClasses) c = kNumObjectClasses;
    return c;
}

class SyntheticDetector : public DetectorBackend {
public:
    explicit SyntheticDetector(const SimConfig& cfg) : cfg_(cfg) {}

    std::string name() const override { return "synthetic_distribution"; }

    StageOutput stage1(const DetectorInput& in) override {
        Rng r = Rng::keyed(cfg_.seed, in.background ? "det_bg_s1" : "det_s1", in.key);
        StageOutput s;
        const double excess_noise = std::max(0.0, in.noise_score - 0.15);
        double mu;
        if (in.frame_has_object) {
            mu = 1.4 + 2.0 * (in.visual_score - 0.6) - 2.5 * excess_noise;
        } else {
            mu = -1.6 + 1.0 * (in.visual_score - 0.3) + 1.0 * excess_noise;
        }
        const double z = r.normal(mu, 0.9);
        s.confidence = sigmoid(z);
        s.predicted_class = draw_class(r, in, s.confidence, 0.55, 0.40);
        s.num_boxes = boxes(r, s.confidence);
        s.latency_ms = r.lognormal_median(cfg_.inference_ms, cfg_.inference_sigma);
        return s;
    }

    StageOutput stage2(const DetectorInput& in, const StageOutput& s1) override {
        Rng r = Rng::keyed(cfg_.seed, in.background ? "det_bg_s2" : "det_s2", in.key);
        StageOutput s;
        // The second pass (e.g. higher input resolution) refines the logit:
        // it raises confidence on real objects and suppresses false alarms.
        const double shift = in.frame_has_object ? r.normal(0.6, 0.5) : r.normal(-0.5, 0.5);
        s.confidence = sigmoid(logit(s1.confidence) + shift);
        s.predicted_class = draw_class(r, in, s.confidence, 0.65, 0.33);
        s.num_boxes = boxes(r, s.confidence);
        s.latency_ms = r.lognormal_median(cfg_.second_pass_cost_ms, cfg_.inference_sigma);
        return s;
    }

    double postprocess_ms(const DetectorInput&, const StageOutput& out) override {
        return cfg_.postprocess_base_ms + cfg_.postprocess_per_box_ms * out.num_boxes;
    }

private:
    const SimConfig& cfg_;

    int draw_class(Rng& r, const DetectorInput& in, double conf, double base, double slope) {
        if (in.frame_has_object) {
            const double p_correct = std::min(0.99, base + slope * conf);
            return r.bernoulli(p_correct) ? in.frame_class : other_class(r, in.frame_class);
        }
        return static_cast<int>(r.uniform_int(1, kNumObjectClasses));
    }
    int boxes(Rng& r, double conf) {
        if (conf < cfg_.detection_threshold) return 0;
        return 1 + r.poisson(0.4);
    }
};

struct TraceRow {
    int predicted_class = CLS_NONE;
    double confidence = 0.0;
    double inference_ms = 0.0;
    double postprocess_ms = 0.0;
    int num_boxes = 0;
    bool has_second = false;
    double s2_confidence = 0.0;
    int s2_predicted_class = CLS_NONE;
    double s2_ms = 0.0;
};

class TraceReplayDetector : public DetectorBackend {
public:
    explicit TraceReplayDetector(const SimConfig& cfg) : cfg_(cfg) { load(cfg.detector_trace); }

    std::string name() const override { return "trace_replay"; }

    StageOutput stage1(const DetectorInput& in) override {
        StageOutput s;
        if (in.background) {
            s.latency_ms = cfg_.trace_background_inference_ms;
            return s;
        }
        const TraceRow& row = get(in.key);
        s.confidence = row.confidence;
        s.predicted_class = row.predicted_class;
        s.num_boxes = row.num_boxes;
        s.latency_ms = row.inference_ms;
        return s;
    }

    StageOutput stage2(const DetectorInput& in, const StageOutput& s1) override {
        StageOutput s = s1;
        if (in.background) {
            s.available = false;
            return s;
        }
        const TraceRow& row = get(in.key);
        if (!row.has_second) {
            s.available = false;  // the trace has no second-pass prediction
            return s;
        }
        s.confidence = row.s2_confidence;
        s.predicted_class = row.s2_predicted_class;
        s.latency_ms = row.s2_ms;
        return s;
    }

    double postprocess_ms(const DetectorInput& in, const StageOutput&) override {
        if (in.background) return cfg_.postprocess_base_ms;
        return get(in.key).postprocess_ms;
    }

private:
    const SimConfig& cfg_;
    std::map<uint64_t, TraceRow> rows_;

    const TraceRow& get(uint64_t id) {
        auto it = rows_.find(id);
        if (it == rows_.end())
            throw std::runtime_error("detector trace has no row for event_id " + std::to_string(id));
        return it->second;
    }

    static int parse_class(const std::string& s) {
        if (s.empty()) return CLS_NONE;
        if (s[0] >= '0' && s[0] <= '9') return std::stoi(s);
        return class_from_name(s);
    }

    void load(const std::string& path) {
        if (path.empty()) throw std::runtime_error("trace_replay backend needs --detector-trace");
        std::ifstream in(path);
        if (!in) throw std::runtime_error("cannot open detector trace: " + path);
        std::string line;
        std::vector<std::string> header;
        auto split = [](const std::string& l) {
            std::vector<std::string> out;
            std::stringstream ss(l);
            std::string tok;
            while (std::getline(ss, tok, ',')) out.push_back(tok);
            return out;
        };
        while (std::getline(in, line)) {
            if (line.empty() || line[0] == '#') continue;
            if (header.empty()) {
                header = split(line);
                continue;
            }
            std::vector<std::string> f = split(line);
            std::map<std::string, std::string> m;
            for (size_t i = 0; i < header.size() && i < f.size(); ++i) m[header[i]] = f[i];
            auto num = [&](const char* k, double def) {
                auto it = m.find(k);
                return (it == m.end() || it->second.empty()) ? def : std::stod(it->second);
            };
            TraceRow r;
            const uint64_t id = static_cast<uint64_t>(num("event_id", 0));
            r.predicted_class = parse_class(m["predicted_class"]);
            r.confidence = num("confidence", 0.0);
            r.inference_ms = num("inference_ms", cfg_.inference_ms);
            r.postprocess_ms = num("postprocess_ms", cfg_.postprocess_base_ms);
            r.num_boxes = static_cast<int>(num("num_boxes", 0));
            if (m.count("second_pass_confidence") && !m["second_pass_confidence"].empty()) {
                r.has_second = true;
                r.s2_confidence = num("second_pass_confidence", 0.0);
                r.s2_predicted_class = parse_class(m["second_pass_predicted_class"]);
                r.s2_ms = num("second_pass_ms", cfg_.second_pass_cost_ms);
            }
            rows_[id] = r;
        }
    }
};

}  // namespace

std::unique_ptr<DetectorBackend> make_detector(const SimConfig& cfg) {
    if (cfg.detector_backend == "synthetic_distribution") return std::make_unique<SyntheticDetector>(cfg);
    if (cfg.detector_backend == "trace_replay") return std::make_unique<TraceReplayDetector>(cfg);
    throw std::runtime_error("unknown detector backend: " + cfg.detector_backend);
}

}  // namespace sim
