#include "workload/workload.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>

#include "core/json.h"
#include "core/rng.h"

namespace sim {

namespace {

double r4(double x) { return std::round(x * 10000.0) / 10000.0; }
double r3(double x) { return std::round(x * 1000.0) / 1000.0; }

// Draft event before final ordering / id assignment.
struct Draft {
    WorkloadEvent ev;
    uint64_t uid = 0;           // generation-order id
    uint64_t replay_of_uid = 0; // uid of the replayed original (0 = none)
};

int draw_class(Rng& r) {
    const double u = r.uniform();
    if (u < 0.50) return CLS_PERSON;
    if (u < 0.75) return CLS_VEHICLE;
    if (u < 0.90) return CLS_ANIMAL;
    return CLS_PACKAGE;
}

void finalize_features(Observable& o) {
    o.motion_score = r4(clamp01(o.motion_score));
    o.visual_score = r4(clamp01(o.visual_score));
    o.temporal_change_score = r4(clamp01(o.temporal_change_score));
    o.sensor_consistency_score = r4(clamp01(o.sensor_consistency_score));
    o.noise_score = r4(clamp01(o.noise_score));
    o.timestamp_ms = r3(o.timestamp_ms);
    o.duration_ms = r3(o.duration_ms);
}

class Generator {
public:
    Generator(const SimConfig& cfg, const ScenarioParams& p)
        : cfg_(cfg), p_(p), T_ms_(cfg.seconds * 1000.0) {}

    std::vector<Draft> run() {
        legit_process();
        if (p_.burst_rate > 0.0) burst_process();
        if (p_.spam_session_rate > 0.0) spam_process();
        if (p_.replay_session_rate > 0.0) replay_process();
        return drafts_;
    }

private:
    const SimConfig& cfg_;
    ScenarioParams p_;
    double T_ms_;
    std::vector<Draft> drafts_;
    uint64_t next_uid_ = 1;
    int64_t next_episode_ = 1;
    int64_t next_burst_ = 1;

    Draft& add(const WorkloadEvent& e) {
        Draft d;
        d.ev = e;
        d.uid = next_uid_++;
        drafts_.push_back(d);
        return drafts_.back();
    }

    double obs_noise(Rng& r) { return clamp01(p_.noise_base + r.normal(0.0, 0.04)); }

    // One legitimate episode starting at t0 (ms).
    void legit_episode(Rng& r, double t0, const std::string& type, int64_t burst_id) {
        const int64_t ep = next_episode_++;
        GroundTruth gt;
        gt.scenario = p_.name;
        gt.episode_id = ep;
        gt.is_legitimate = true;
        gt.burst_id = burst_id;
        gt.episode_type = type;
        int n_obs = 1;
        double visibility = 0.0;
        if (type == "object") {
            gt.object_present = true;
            gt.object_class = draw_class(r);
            gt.frame_has_object = true;
            gt.frame_object_class = gt.object_class;
            gt.ground_truth_action = "detect";
            n_obs = 1 + r.poisson(2.0);  // repeated observations of the same object
            visibility = r.normal(0.70, 0.12);
        } else if (type == "benign_motion") {
            gt.ground_truth_action = "ignore";
            n_obs = 1 + r.poisson(0.5);
        } else {  // noise
            gt.ground_truth_action = "ignore";
            n_obs = 1 + r.poisson(0.3);
        }
        double t = t0;
        Observable prev;
        for (int k = 0; k < n_obs; ++k) {
            WorkloadEvent e;
            e.gt = gt;
            Observable& o = e.obs;
            o.timestamp_ms = t;
            o.noise_score = obs_noise(r);
            const double excess_noise = std::max(0.0, o.noise_score - 0.15);
            if (type == "object") {
                o.duration_ms = r.uniform(400.0, 1500.0);
                const bool static_frame = (k > 0) && r.bernoulli(0.15);
                if (static_frame) {
                    // Static scene: the next frame is nearly identical and
                    // has the same perceptual hash as the previous one.
                    o.motion_score = prev.motion_score + r.normal(0.0, 0.005);
                    o.visual_score = prev.visual_score + r.normal(0.0, 0.005);
                    o.temporal_change_score = prev.temporal_change_score + r.normal(0.0, 0.005);
                    o.sensor_consistency_score = prev.sensor_consistency_score + r.normal(0.0, 0.005);
                    o.content_signature = prev.content_signature;
                } else {
                    o.visual_score = visibility + r.normal(0.0, 0.06) - 0.3 * excess_noise;
                    o.motion_score = r.normal(0.62, 0.15);
                    o.temporal_change_score = o.motion_score + r.normal(0.0, 0.08);
                    o.sensor_consistency_score = r.normal(0.86, 0.06) - 0.25 * excess_noise;
                    o.content_signature = r.next_u64();
                }
            } else if (type == "benign_motion") {
                o.duration_ms = r.uniform(300.0, 1500.0);
                o.motion_score = r.normal(0.55, 0.18);
                o.visual_score = r.normal(0.30, 0.12);
                o.temporal_change_score = o.motion_score + r.normal(0.0, 0.10);
                o.sensor_consistency_score = r.normal(0.80, 0.08) - 0.25 * excess_noise;
                o.content_signature = r.next_u64();
            } else {
                o.duration_ms = r.uniform(100.0, 600.0);
                o.noise_score = clamp01(p_.noise_base + 0.25 + r.normal(0.0, 0.08));
                o.motion_score = r.normal(0.30, 0.15);
                o.visual_score = r.normal(0.22, 0.10);
                o.temporal_change_score = r.normal(0.50, 0.20);
                o.sensor_consistency_score = r.normal(0.60, 0.15);
                o.content_signature = r.next_u64();
            }
            finalize_features(o);
            prev = o;
            add(e);
            t += r.uniform(500.0, 1500.0);
        }
    }

    std::string draw_type(Rng& r) {
        const double u = r.uniform();
        if (u < p_.p_object) return "object";
        if (u < p_.p_object + p_.p_benign) return "benign_motion";
        return "noise";
    }

    // Markov-modulated Poisson process for legitimate activity.
    void legit_process() {
        Rng r(hash_combine(cfg_.seed, hash_str("legit")));
        const double scale = cfg_.arrival_scale;
        bool active = r.bernoulli(p_.calm_to_active / (p_.calm_to_active + p_.active_to_calm));
        double t = 0.0;
        double next_switch = r.exponential(active ? p_.active_to_calm : p_.calm_to_active) * 1000.0;
        while (true) {
            const double rate = (active ? p_.rate_active : p_.rate_calm) * scale;
            const double dt = r.exponential(rate) * 1000.0;
            if (t + dt >= next_switch) {
                // Memorylessness lets us restart the arrival clock at the switch.
                t = next_switch;
                active = !active;
                next_switch = t + r.exponential(active ? p_.active_to_calm : p_.calm_to_active) * 1000.0;
                if (t >= T_ms_) break;
                continue;
            }
            t += dt;
            if (t >= T_ms_) break;
            legit_episode(r, t, draw_type(r), -1);
        }
    }

    void burst_process() {
        Rng r(hash_combine(cfg_.seed, hash_str("burst")));
        double t = 0.0;
        while (true) {
            t += r.exponential(p_.burst_rate * cfg_.arrival_scale) * 1000.0;
            if (t >= T_ms_) break;
            const int64_t bid = next_burst_++;
            const int n = static_cast<int>(r.uniform_int(p_.burst_min, p_.burst_max));
            const double span = r.uniform(0.3, 1.0) * p_.burst_span_s * 1000.0;
            for (int i = 0; i < n; ++i) {
                const double onset = t + r.uniform(0.0, span);
                legit_episode(r, onset, r.bernoulli(0.8) ? "object" : "benign_motion", bid);
            }
        }
    }

    void spam_process() {
        Rng r(hash_combine(cfg_.seed, hash_str("spam")));
        double t = 0.0;
        while (true) {
            t += r.exponential(p_.spam_session_rate) * 1000.0;
            if (t >= T_ms_) break;
            const double end = t + r.exponential(1.0 / p_.spam_session_mean_s) * 1000.0;
            const int64_t ep = next_episode_++;
            double ts = t;
            while (true) {
                ts += r.exponential(p_.spam_rate) * 1000.0;
                if (ts >= end || ts >= T_ms_) break;
                WorkloadEvent e;
                GroundTruth& gt = e.gt;
                gt.scenario = p_.name;
                gt.episode_id = ep;
                gt.is_legitimate = false;
                gt.attack_type = "trigger_spam";
                gt.episode_type = "attack";
                gt.ground_truth_action = "block";
                Observable& o = e.obs;
                o.timestamp_ms = ts;
                o.duration_ms = r.uniform(100.0, 300.0);
                o.noise_score = obs_noise(r);
                if (r.bernoulli(cfg_.spam_sophistication)) {
                    // Sophisticated injection: all sensing channels agree.
                    o.motion_score = r.normal(0.70, 0.10);
                    o.visual_score = r.normal(0.65, 0.10);
                    o.temporal_change_score = o.motion_score + r.normal(0.0, 0.06);
                    o.sensor_consistency_score = r.normal(0.85, 0.06);
                } else {
                    // Naive injection on the motion/trigger channel only.
                    o.motion_score = r.uniform(0.70, 1.00);
                    o.visual_score = r.uniform(0.30, 0.80);
                    o.temporal_change_score = r.uniform(0.20, 0.70);
                    o.sensor_consistency_score = r.uniform(0.10, 0.50);
                }
                o.content_signature = r.next_u64();
                finalize_features(o);
                add(e);
            }
            t = std::max(t, end);
        }
    }

    void replay_process() {
        Rng r(hash_combine(cfg_.seed, hash_str("replay")));
        // Snapshot of legitimate object observations recorded by the attacker.
        std::vector<size_t> originals;
        for (size_t i = 0; i < drafts_.size(); ++i)
            if (drafts_[i].ev.gt.is_legitimate && drafts_[i].ev.gt.episode_type == "object") originals.push_back(i);
        std::map<int64_t, std::vector<size_t>> by_episode;
        for (size_t i : originals) by_episode[drafts_[i].ev.gt.episode_id].push_back(i);
        double t = 0.0;
        while (true) {
            t += r.exponential(p_.replay_session_rate) * 1000.0;
            if (t >= T_ms_) break;
            // Candidate recorded episodes: onset in [t - 1800 s, t - 10 s].
            std::vector<int64_t> cands;
            for (const auto& kv : by_episode) {
                const double onset = drafts_[kv.second.front()].ev.obs.timestamp_ms;
                if (onset <= t - 10000.0 && onset >= t - 1800000.0) cands.push_back(kv.first);
            }
            if (cands.empty()) continue;
            const int64_t chosen = cands[static_cast<size_t>(r.uniform_int(0, static_cast<int64_t>(cands.size()) - 1))];
            const std::vector<size_t> seq = by_episode[chosen];
            const int64_t ep = next_episode_++;
            const int reps = static_cast<int>(r.uniform_int(1, 3));
            const double onset0 = drafts_[seq.front()].ev.obs.timestamp_ms;
            const double seq_len = drafts_[seq.back()].ev.obs.timestamp_ms - onset0 + drafts_[seq.back()].ev.obs.duration_ms;
            double base = t;
            for (int rep = 0; rep < reps; ++rep) {
                for (size_t idx : seq) {
                    const WorkloadEvent orig = drafts_[idx].ev;
                    const uint64_t orig_uid = drafts_[idx].uid;
                    WorkloadEvent e;
                    e.obs = orig.obs;
                    // Timing reuse: same relative offsets as the recording.
                    e.obs.timestamp_ms = base + (orig.obs.timestamp_ms - onset0);
                    if (r.bernoulli(cfg_.replay_perturb_prob)) {
                        e.obs.motion_score += r.normal(0.0, 0.03);
                        e.obs.visual_score += r.normal(0.0, 0.03);
                        e.obs.temporal_change_score += r.normal(0.0, 0.03);
                        e.obs.sensor_consistency_score += r.normal(0.0, 0.03);
                        e.obs.content_signature = r.next_u64();
                    }
                    finalize_features(e.obs);
                    GroundTruth& gt = e.gt;
                    gt.scenario = p_.name;
                    gt.episode_id = ep;
                    gt.is_legitimate = false;
                    gt.object_present = false;
                    gt.object_class = CLS_NONE;
                    gt.attack_type = "replay";
                    gt.episode_type = "attack";
                    gt.ground_truth_action = "block";
                    // The replayed frame still shows the recorded object.
                    gt.frame_has_object = orig.gt.frame_has_object;
                    gt.frame_object_class = orig.gt.frame_object_class;
                    Draft& d = add(e);
                    d.replay_of_uid = orig_uid;
                }
                base += seq_len + r.uniform(200.0, 1000.0);
            }
        }
    }
};

const char* kClassNames[] = {"none", "person", "vehicle", "animal", "package"};

}  // namespace

const char* class_name(int cls) {
    if (cls < 0 || cls > kNumObjectClasses) return "none";
    return kClassNames[cls];
}

int class_from_name(const std::string& name) {
    for (int i = 0; i <= kNumObjectClasses; ++i)
        if (name == kClassNames[i]) return i;
    return CLS_NONE;
}

ScenarioParams scenario_params(const std::string& scenario, const SimConfig& cfg) {
    ScenarioParams p;
    p.name = scenario;
    // "normal" is the reference environment; other scenarios modify it.
    p.rate_calm = 1.0 / 60.0;
    p.rate_active = 1.0 / 12.0;
    p.calm_to_active = 1.0 / 600.0;
    p.active_to_calm = 1.0 / 180.0;
    p.p_object = 0.55;
    p.p_benign = 0.30;
    p.p_noise = 0.15;
    p.noise_base = 0.12;
    p.burst_rate = 1.0 / 1200.0;
    p.burst_min = 3;
    p.burst_max = 6;
    p.burst_span_s = 5.0;
    const double ai = cfg.attack_intensity;
    if (scenario == "quiet") {
        p.rate_calm = 1.0 / 240.0;
        p.rate_active = 1.0 / 40.0;
        p.calm_to_active = 1.0 / 1800.0;
        p.active_to_calm = 1.0 / 300.0;
        p.p_object = 0.60;
        p.p_benign = 0.30;
        p.p_noise = 0.10;
        p.noise_base = 0.08;
        p.burst_rate = 0.0;
    } else if (scenario == "busy") {
        p.rate_calm = 1.0 / 15.0;
        p.rate_active = 1.0 / 4.0;
        p.calm_to_active = 1.0 / 300.0;
        p.active_to_calm = 1.0 / 300.0;
        p.p_object = 0.65;
        p.p_benign = 0.25;
        p.p_noise = 0.10;
        p.noise_base = 0.15;
        p.burst_rate = 1.0 / 600.0;
    } else if (scenario == "burst") {
        p.burst_rate = 1.0 / 180.0;
        p.burst_min = 8;
        p.burst_max = 20;
        p.burst_span_s = 10.0;
    } else if (scenario == "noisy") {
        p.p_object = 0.45;
        p.p_benign = 0.25;
        p.p_noise = 0.30;
        p.noise_base = 0.40;
    } else if (scenario == "trigger_spam") {
        p.spam_session_rate = ai / 300.0;
    } else if (scenario == "replay") {
        p.replay_session_rate = ai / 240.0;
    } else if (scenario == "mixed") {
        p.burst_rate = 1.0 / 900.0;
        p.spam_session_rate = 0.5 * ai / 300.0;
        p.replay_session_rate = 0.5 * ai / 240.0;
    }
    return p;
}

std::string scenario_params_json(const ScenarioParams& p) {
    char buf[1024];
    std::snprintf(buf, sizeof(buf),
                  "{\"name\": \"%s\", \"rate_calm_per_s\": %.6g, \"rate_active_per_s\": %.6g, "
                  "\"calm_to_active_per_s\": %.6g, \"active_to_calm_per_s\": %.6g, \"p_object\": %.6g, "
                  "\"p_benign\": %.6g, \"p_noise\": %.6g, \"noise_base\": %.6g, \"burst_rate_per_s\": %.6g, "
                  "\"burst_min\": %d, \"burst_max\": %d, \"burst_span_s\": %.6g, \"spam_session_rate_per_s\": %.6g, "
                  "\"spam_session_mean_s\": %.6g, \"spam_rate_per_s\": %.6g, \"replay_session_rate_per_s\": %.6g}",
                  p.name.c_str(), p.rate_calm, p.rate_active, p.calm_to_active, p.active_to_calm, p.p_object,
                  p.p_benign, p.p_noise, p.noise_base, p.burst_rate, p.burst_min, p.burst_max, p.burst_span_s,
                  p.spam_session_rate, p.spam_session_mean_s, p.spam_rate, p.replay_session_rate);
    return buf;
}

Workload generate_workload(const SimConfig& cfg) {
    const ScenarioParams p = scenario_params(cfg.scenario, cfg);
    Generator gen(cfg, p);
    std::vector<Draft> drafts = gen.run();
    const double T = cfg.seconds * 1000.0;
    // Workload duration is obeyed: drop late onsets, clip durations to T.
    std::vector<Draft> kept;
    for (Draft& d : drafts) {
        if (d.ev.obs.timestamp_ms >= T) continue;
        if (d.ev.obs.timestamp_ms + d.ev.obs.duration_ms > T)
            d.ev.obs.duration_ms = r3(T - d.ev.obs.timestamp_ms);
        if (d.ev.obs.duration_ms <= 0.0) continue;
        kept.push_back(d);
    }
    std::stable_sort(kept.begin(), kept.end(), [](const Draft& a, const Draft& b) {
        if (a.ev.obs.timestamp_ms != b.ev.obs.timestamp_ms) return a.ev.obs.timestamp_ms < b.ev.obs.timestamp_ms;
        return a.uid < b.uid;
    });
    std::map<uint64_t, uint64_t> uid_to_id;
    for (size_t i = 0; i < kept.size(); ++i) uid_to_id[kept[i].uid] = i + 1;
    Workload wl;
    wl.scenario = cfg.scenario;
    wl.seed = cfg.seed;
    wl.seconds = cfg.seconds;
    for (size_t i = 0; i < kept.size(); ++i) {
        WorkloadEvent e = kept[i].ev;
        e.obs.event_id = i + 1;
        if (kept[i].replay_of_uid) {
            auto it = uid_to_id.find(kept[i].replay_of_uid);
            e.gt.replay_id = (it != uid_to_id.end()) ? static_cast<int64_t>(it->second) : -1;
        }
        wl.events.push_back(e);
    }
    return wl;
}

std::string hex64(uint64_t v) {
    char buf[17];
    std::snprintf(buf, sizeof(buf), "%016llx", static_cast<unsigned long long>(v));
    return buf;
}

namespace {

uint64_t parse_hex_word(const std::string& s, size_t word) {
    if (s.size() < 16 * (word + 1)) throw std::runtime_error("hex field too short: " + s);
    return std::strtoull(s.substr(16 * word, 16).c_str(), nullptr, 16);
}

std::string r2_jsonl_suffix(const Observable& o) {
    char buf[512];
    std::snprintf(buf, sizeof(buf),
                  ",\"edge_change_score\":%.4f,\"r2_motion\":%.4f,\"r2_temporal\":%.4f,\"r2_visual\":%.4f,"
                  "\"r2_consistency\":%.4f,\"mog2_fg\":%.5f,\"motion_cells\":\"%s\",\"fg_count\":%d",
                  o.edge_change_score, o.r2_motion, o.r2_temporal, o.r2_visual, o.r2_consistency, o.mog2_fg,
                  hex64(o.motion_cells).c_str(), o.fg_count);
    std::string out = buf;
    out += ",\"fp256\":\"";
    for (uint64_t w : o.fp256) out += hex64(w);
    out += "\",\"fg768\":\"";
    for (uint64_t w : o.fg768) out += hex64(w);
    out += "\"";
    if (o.has_thumb) {
        out += ",\"thumb192\":\"";
        char h[3];
        for (int k = 0; k < 192; ++k) {
            std::snprintf(h, sizeof(h), "%02x", o.thumb192[k]);
            out += h;
        }
        out += "\"";
    }
    return out;
}

}  // namespace

std::string workload_event_to_jsonl(const WorkloadEvent& e) {
    const Observable& o = e.obs;
    const GroundTruth& g = e.gt;
    char buf[1024];
    std::snprintf(buf, sizeof(buf),
                  "{\"event_id\":%llu,\"timestamp_ms\":%.3f,\"duration_ms\":%.3f,\"scenario\":\"%s\","
                  "\"episode_id\":%lld,\"episode_type\":\"%s\",\"is_legitimate\":%s,\"object_present\":%s,"
                  "\"object_class\":\"%s\",\"motion_score\":%.4f,\"visual_score\":%.4f,"
                  "\"temporal_change_score\":%.4f,\"sensor_consistency_score\":%.4f,\"noise_score\":%.4f,"
                  "\"content_signature\":\"%s\",\"attack_type\":\"%s\",\"replay_id\":%lld,\"burst_id\":%lld,"
                  "\"ground_truth_action\":\"%s\",\"frame_has_object\":%s,\"frame_object_class\":\"%s\"}",
                  static_cast<unsigned long long>(o.event_id), o.timestamp_ms, o.duration_ms, g.scenario.c_str(),
                  static_cast<long long>(g.episode_id), g.episode_type.c_str(), g.is_legitimate ? "true" : "false",
                  g.object_present ? "true" : "false", class_name(g.object_class), o.motion_score, o.visual_score,
                  o.temporal_change_score, o.sensor_consistency_score, o.noise_score,
                  hex64(o.content_signature).c_str(), g.attack_type.c_str(), static_cast<long long>(g.replay_id),
                  static_cast<long long>(g.burst_id), g.ground_truth_action.c_str(),
                  g.frame_has_object ? "true" : "false", class_name(g.frame_object_class));
    std::string line = buf;
    if (o.has_r2) {
        // R2 fields are appended inside the object; R1 workloads are unchanged.
        line.pop_back();
        line += r2_jsonl_suffix(o) + "}";
    }
    return line;
}

void save_workload(const Workload& wl, const std::string& path, const SimConfig& cfg) {
    {
        std::ofstream out(path, std::ios::binary);
        if (!out) throw std::runtime_error("cannot write workload: " + path);
        for (const auto& e : wl.events) out << workload_event_to_jsonl(e) << '\n';
    }
    const ScenarioParams p = scenario_params(wl.scenario, cfg);
    std::ofstream meta(path + ".meta.json", std::ios::binary);
    meta << "{\n  \"generator_version\": \"" << kWorkloadGeneratorVersion << "\",\n"
         << "  \"scenario\": \"" << wl.scenario << "\",\n"
         << "  \"seed\": " << wl.seed << ",\n"
         << "  \"seconds\": " << wl.seconds << ",\n"
         << "  \"attack_intensity\": " << cfg.attack_intensity << ",\n"
         << "  \"arrival_scale\": " << cfg.arrival_scale << ",\n"
         << "  \"spam_sophistication\": " << cfg.spam_sophistication << ",\n"
         << "  \"replay_perturb_prob\": " << cfg.replay_perturb_prob << ",\n"
         << "  \"num_events\": " << wl.events.size() << ",\n"
         << "  \"scenario_params\": " << scenario_params_json(p) << ",\n"
         << "  \"workload_hash_fnv1a64\": \"" << file_hash_hex(path) << "\"\n}\n";
}

Workload load_workload(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open workload: " + path);
    Workload wl;
    std::string line;
    size_t lineno = 0;
    double max_end = 0.0;
    while (std::getline(in, line)) {
        ++lineno;
        if (line.empty()) continue;
        JsonValue v = json_parse(line);
        WorkloadEvent e;
        Observable& o = e.obs;
        GroundTruth& g = e.gt;
        o.event_id = static_cast<uint64_t>(v.at("event_id").as_number());
        o.timestamp_ms = v.at("timestamp_ms").as_number();
        o.duration_ms = v.at("duration_ms").as_number();
        o.motion_score = v.at("motion_score").as_number();
        o.visual_score = v.at("visual_score").as_number();
        o.temporal_change_score = v.at("temporal_change_score").as_number();
        o.sensor_consistency_score = v.at("sensor_consistency_score").as_number();
        o.noise_score = v.at("noise_score").as_number();
        o.content_signature = std::strtoull(v.at("content_signature").as_string().c_str(), nullptr, 16);
        g.scenario = v.at("scenario").as_string();
        g.episode_id = v.has("episode_id") ? static_cast<int64_t>(v.at("episode_id").as_number()) : -1;
        g.episode_type = v.has("episode_type") ? v.at("episode_type").as_string() : "";
        g.is_legitimate = v.at("is_legitimate").as_bool();
        g.object_present = v.at("object_present").as_bool();
        g.object_class = class_from_name(v.at("object_class").as_string());
        g.attack_type = v.at("attack_type").as_string();
        g.replay_id = static_cast<int64_t>(v.at("replay_id").as_number());
        g.burst_id = static_cast<int64_t>(v.at("burst_id").as_number());
        g.ground_truth_action = v.at("ground_truth_action").as_string();
        g.frame_has_object = v.has("frame_has_object") ? v.at("frame_has_object").as_bool() : g.object_present;
        g.frame_object_class = v.has("frame_object_class") ? class_from_name(v.at("frame_object_class").as_string())
                                                           : g.object_class;
        if (v.has("fp256")) {
            o.has_r2 = true;
            o.edge_change_score = v.at("edge_change_score").as_number();
            o.r2_motion = v.at("r2_motion").as_number();
            o.r2_temporal = v.at("r2_temporal").as_number();
            o.r2_visual = v.at("r2_visual").as_number();
            o.r2_consistency = v.at("r2_consistency").as_number();
            o.mog2_fg = v.has("mog2_fg") ? v.at("mog2_fg").as_number() : 0.0;
            o.motion_cells = std::strtoull(v.at("motion_cells").as_string().c_str(), nullptr, 16);
            o.fg_count = static_cast<int>(v.at("fg_count").as_number());
            const std::string fp = v.at("fp256").as_string(), fg = v.at("fg768").as_string();
            for (size_t k = 0; k < 4; ++k) o.fp256[k] = parse_hex_word(fp, k);
            for (size_t k = 0; k < 12; ++k) o.fg768[k] = parse_hex_word(fg, k);
        }
        if (v.has("thumb192")) {
            const std::string th = v.at("thumb192").as_string();
            if (th.size() != 384) throw std::runtime_error("thumb192 must have 384 hex digits");
            o.has_thumb = true;
            for (size_t k = 0; k < 192; ++k)
                o.thumb192[k] = static_cast<uint8_t>(std::strtoul(th.substr(2 * k, 2).c_str(), nullptr, 16));
        }
        if (!wl.events.empty() && o.timestamp_ms < wl.events.back().obs.timestamp_ms)
            throw std::runtime_error("workload not sorted by timestamp at line " + std::to_string(lineno));
        max_end = std::max(max_end, o.timestamp_ms + o.duration_ms);
        if (wl.scenario.empty()) wl.scenario = g.scenario;
        wl.events.push_back(e);
    }
    wl.seconds = max_end / 1000.0;  // lower bound; caller may set the real horizon
    return wl;
}

std::string file_hash_hex(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return "";
    uint64_t h = 0xcbf29ce484222325ULL;
    char buf[65536];
    while (in) {
        in.read(buf, sizeof(buf));
        const std::streamsize n = in.gcount();
        for (std::streamsize i = 0; i < n; ++i) {
            h ^= static_cast<unsigned char>(buf[i]);
            h *= 0x100000001b3ULL;
        }
    }
    return hex64(h);
}

}  // namespace sim
