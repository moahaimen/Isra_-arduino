#include "config/sim_config.h"

#include <cstdio>
#include <cstdlib>
#include <functional>
#include <map>
#include <sstream>
#include <stdexcept>

#include "core/json.h"

namespace sim {

namespace {

const char* kModes[] = {"always_on", "motion_only", "fixed_threshold", "event",       "event_no_early_exit",
                        "secure",    "robust_event", "robust_secure",  "mog2_event", "ugs_event", "ugs_secure"};
const char* kScenarios[] = {"quiet", "normal", "busy", "burst", "noisy", "trigger_spam", "replay", "mixed"};

std::string normalize(std::string name) {
    while (!name.empty() && name[0] == '-') name.erase(0, 1);
    for (char& c : name)
        if (c == '-') c = '_';
    return name;
}

bool parse_bool(const std::string& v) {
    if (v == "1" || v == "true" || v == "on" || v == "yes") return true;
    if (v == "0" || v == "false" || v == "off" || v == "no") return false;
    throw std::runtime_error("invalid boolean value: " + v);
}

double parse_double(const std::string& v) {
    char* end = nullptr;
    double d = std::strtod(v.c_str(), &end);
    if (end == v.c_str() || *end != '\0') throw std::runtime_error("invalid number: " + v);
    return d;
}

std::string fmt(double d) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%.10g", d);
    return buf;
}

struct Param {
    std::function<void(SimConfig&, const std::string&)> set;
    std::function<std::string(const SimConfig&)> json;  // JSON-encoded value
    std::string help;
};

// Ordered registry: name -> accessors. Order is preserved for config.json.
std::vector<std::pair<std::string, Param>>& registry() {
    static std::vector<std::pair<std::string, Param>> reg;
    if (!reg.empty()) return reg;
#define P_DBL(field, help)                                                                       \
    reg.push_back({#field, Param{[](SimConfig& c, const std::string& v) { c.field = parse_double(v); }, \
                                 [](const SimConfig& c) { return fmt(c.field); }, help}})
#define P_INT(field, help)                                                                                 \
    reg.push_back({#field, Param{[](SimConfig& c, const std::string& v) { c.field = static_cast<int>(parse_double(v)); }, \
                                 [](const SimConfig& c) { return std::to_string(c.field); }, help}})
#define P_U64(field, help)                                                                                       \
    reg.push_back({#field, Param{[](SimConfig& c, const std::string& v) { c.field = std::strtoull(v.c_str(), nullptr, 10); }, \
                                 [](const SimConfig& c) { return std::to_string(c.field); }, help}})
#define P_BOOL(field, help)                                                                      \
    reg.push_back({#field, Param{[](SimConfig& c, const std::string& v) { c.field = parse_bool(v); }, \
                                 [](const SimConfig& c) { return std::string(c.field ? "true" : "false"); }, help}})
#define P_STR(field, help)                                                                \
    reg.push_back({#field, Param{[](SimConfig& c, const std::string& v) { c.field = v; }, \
                                 [](const SimConfig& c) { return "\"" + json_escape(c.field) + "\""; }, help}})

    P_STR(mode, "operating mode");
    P_STR(scenario, "workload scenario");
    P_U64(seed, "random seed");
    P_DBL(seconds, "simulated duration in seconds");
    P_STR(workload, "replay an existing workload JSONL");
    P_STR(save_workload, "save the generated workload JSONL");
    P_STR(out_dir, "output directory for this run");
    P_STR(power_model, "power model JSON");
    P_STR(log_level, "JSONL event log level: full|decisions|none");
    P_DBL(attack_intensity, "attack intensity multiplier");
    P_DBL(arrival_scale, "legitimate arrival-rate multiplier");
    P_DBL(spam_sophistication, "fraction of spam triggers mimicking consistent sensors");
    P_DBL(replay_perturb_prob, "fraction of replays perturbed to defeat exact hashing");
    P_STR(watcher_kind, "watcher decision rule: score|motion|robust|mog2");
    P_STR(watcher_frontend, "watcher feature front end: basic|r2 (gain-compensated)");
    P_DBL(w_motion, "watcher weight for motion_score");
    P_DBL(w_visual, "watcher weight for visual_score");
    P_DBL(w_temporal, "watcher weight for temporal_change_score");
    P_DBL(w_consistency, "watcher weight for sensor_consistency_score");
    P_DBL(trigger_threshold, "watcher score threshold theta");
    P_DBL(motion_threshold, "motion-only baseline threshold");
    P_DBL(cooldown_ms, "minimum time between triggers");
    P_BOOL(cooldown, "enable trigger cooldown");
    P_BOOL(adaptive_trigger, "enable noise-adaptive threshold");
    P_DBL(adaptive_gain, "adaptive threshold gain");
    P_DBL(adaptive_noise_ref, "adaptive threshold noise reference");
    P_DBL(adaptive_ewma_alpha, "adaptive threshold EWMA factor");
    P_DBL(m4_process_ms, "M4 watcher processing time per observation");
    P_INT(robust_bg_window, "robust watcher: background score history length");
    P_INT(robust_bg_min, "robust watcher: history needed before the robust threshold is used");
    P_DBL(robust_z_on, "robust watcher: on threshold in robust z units");
    P_DBL(robust_z_off, "robust watcher: off (hysteresis) threshold in robust z units");
    P_DBL(robust_theta_min, "robust watcher: lower bound of the on threshold");
    P_DBL(robust_theta_max, "robust watcher: upper bound of the on threshold");
    P_DBL(robust_sigma_floor, "robust watcher: minimum robust sigma");
    P_INT(robust_persist_k, "robust watcher: consecutive frames above threshold to activate");
    P_INT(robust_release_k, "robust watcher: consecutive frames below off threshold to release");
    P_BOOL(robust_threshold, "robust watcher: robust noise-normalised threshold (off = fixed theta_max)");
    P_BOOL(content_cooldown, "robust watcher: per-content cooldown (off = one global cooldown)");
    P_DBL(content_cooldown_ms, "robust watcher: re-trigger period of one content region");
    P_DBL(content_overlap_thr, "robust watcher/gate: cell-mask overlap for the same content");
    P_DBL(region_ttl_ms, "robust watcher: forget a content region after this idle time");
    P_DBL(mog2_threshold, "MOG2 baseline: foreground-fraction trigger threshold");
    P_DBL(ugs_sigma_floor, "UGS: minimum robust sigma");
    P_DBL(ugs_b_prior, "UGS: empty-scene baseline prior");
    P_DBL(ugs_sigma_prior, "UGS: scale prior");
    P_DBL(ugs_b_cap, "UGS: cap of the learned baseline");
    P_DBL(ugs_sigma_cap, "UGS: cap of the learned scale");
    P_DBL(ugs_s_floor, "UGS: absolute score floor for evidence");
    P_DBL(ugs_z0, "UGS: evidence offset in robust z units");
    P_DBL(ugs_e_max, "UGS: per-frame evidence cap");
    P_DBL(ugs_rho, "UGS: evidence accumulator leak factor");
    P_DBL(ugs_a_on, "UGS: activation threshold of the accumulator");
    P_DBL(ugs_a_off, "UGS: release threshold of the accumulator");
    P_DBL(ugs_dt_retry_ms, "UGS: re-check period of an unverified region");
    P_INT(ugs_k_retry, "UGS: re-checks before a region is barren");
    P_DBL(ugs_dt_track_ms, "UGS: refresh period of a confirmed region");
    P_DBL(ugs_dt_barren_ms, "UGS: base period of a barren region (doubles per request)");
    P_DBL(ugs_barren_cap_ms, "UGS: cap of the barren back-off");
    P_DBL(ugs_region_ttl_ms, "UGS: forget a region after this idle time");
    P_INT(ugs_max_inflight, "UGS: defer non-novel requests while this many are outstanding");
    P_DBL(ugs_awake_factor, "UGS: period multiplier while the M7 is awake");
    P_BOOL(ugs_feedback, "UGS: use M7 result feedback");
    P_BOOL(ugs_novelty, "UGS: per-content regions (off = one shared region)");
    P_BOOL(ugs_persistence, "UGS: evidence accumulation (off = single-frame activation)");
    P_BOOL(ug_replay, "R3 gate: temporal-context replay check");
    P_DBL(ug_min_age_ms, "R3 gate: minimum age of a stale match");
    P_INT(ug_fg_min, "R3 gate: minimum foreground bits to check / store");
    P_DBL(ug_d_abs, "R3 gate: absolute block-difference threshold");
    P_DBL(ug_d_rel, "R3 gate: relative block-difference threshold");
    P_INT(ug_k_match, "R3 gate: max changed blocks for a stale match");
    P_INT(ug_k_jump, "R3 gate: min changed blocks vs the previous frame");
    P_INT(ug_margin, "R3 gate: n_old + margin <= n_prev");
    P_INT(ug_history, "R3 gate: thumbnail history capacity");
    P_BOOL(ug_budget, "R3 gate: global wake budget");
    P_DBL(ug_capacity, "R3 gate: budget capacity");
    P_DBL(ug_refill_per_s, "R3 gate: budget refill per second");
    P_DBL(ug_novelty_capacity, "R3 gate: reserved novelty budget capacity");
    P_DBL(ug_novelty_refill_per_s, "R3 gate: novelty budget refill per second");
    P_BOOL(security, "enable the security gate");
    P_STR(security_kind, "security gate: legacy|robust");
    P_BOOL(rate_limit_enabled, "enable trigger rate limiting");
    P_INT(rate_limit, "max accepted triggers per rate window");
    P_DBL(rate_window_ms, "rate-limit window");
    P_BOOL(replay_protection, "enable replay detection");
    P_DBL(replay_window_ms, "replay detection window");
    P_DBL(replay_feature_eps, "near-duplicate feature distance for replay detection");
    P_BOOL(duplicate_protection, "enable duplicate detection");
    P_DBL(duplicate_window_ms, "duplicate detection window");
    P_BOOL(burst_detection, "enable burst anomaly detection");
    P_INT(burst_threshold, "max trigger candidates per burst window");
    P_DBL(burst_window_ms, "burst detection window");
    P_BOOL(consistency_check, "enable sensor consistency check");
    P_DBL(consistency_threshold, "minimum consistency to accept");
    P_INT(security_history, "security history ring-buffer capacity");
    P_DBL(security_process_ms, "security processing time per trigger");
    P_DBL(debug_random_block_prob, "DEBUG ONLY legacy random blocking probability");
    P_BOOL(rg_consistency, "robust gate: consistency check");
    P_DBL(rg_consistency_threshold, "robust gate: minimum compensated consistency");
    P_BOOL(rg_replay, "robust gate: content-fingerprint replay check");
    P_DBL(rg_replay_window_ms, "robust gate: replay history window");
    P_DBL(rg_replay_min_age_ms, "robust gate: minimum age of a replay match");
    P_DBL(rg_fg_jaccard_thr, "robust gate: foreground-mask Jaccard for a replay match");
    P_INT(rg_dhash_max, "robust gate: max dHash-256 Hamming distance for a replay match");
    P_INT(rg_fg_min, "robust gate: minimum foreground bits for replay checking/history");
    P_INT(rg_history, "robust gate: fingerprint history capacity");
    P_BOOL(rg_content_bucket, "robust gate: per-content token bucket");
    P_DBL(rg_content_capacity, "robust gate: per-content bucket capacity");
    P_DBL(rg_content_refill_per_s, "robust gate: per-content refill rate");
    P_DBL(rg_content_ttl_ms, "robust gate: per-content slot lifetime");
    P_BOOL(rg_global_bucket, "robust gate: global token bucket");
    P_DBL(rg_global_capacity, "robust gate: global bucket capacity");
    P_DBL(rg_global_refill_per_s, "robust gate: global refill rate");
    P_BOOL(rg_emergency, "robust gate: emergency budget for novel high-z content");
    P_DBL(rg_emergency_capacity, "robust gate: emergency budget capacity");
    P_DBL(rg_emergency_refill_per_s, "robust gate: emergency budget refill rate");
    P_DBL(rg_z_emergency, "robust gate: minimum watcher z for the emergency budget");
    P_DBL(rpc_latency_ms, "RPC base transmission latency");
    P_DBL(rpc_jitter_ms, "RPC jitter scale (half-normal)");
    P_DBL(rpc_loss, "RPC request loss probability");
    P_INT(rpc_queue_capacity, "M7 request queue capacity");
    P_STR(detector_backend, "synthetic_distribution|trace_replay");
    P_STR(detector_trace, "detector trace CSV for trace_replay");
    P_STR(trace_timing, "trace_replay latencies: trace|simulated");
    P_DBL(inference_ms, "median stage-1 inference latency");
    P_DBL(inference_sigma, "log-normal sigma of inference latency");
    P_DBL(second_pass_cost_ms, "median stage-2 latency");
    P_DBL(postprocess_base_ms, "postprocessing base time");
    P_DBL(postprocess_per_box_ms, "postprocessing time per box");
    P_DBL(detection_threshold, "confidence threshold for a positive detection");
    P_BOOL(early_exit, "enable early exit");
    P_DBL(early_exit_threshold, "exit after stage 1 when confidence >= this");
    P_DBL(early_exit_low_threshold, "exit after stage 1 when confidence <= this");
    P_DBL(m7_wakeup_ms, "M7 wake-up latency");
    P_DBL(m7_linger_ms, "M7 awake idle time before sleeping");
    P_DBL(trace_background_inference_ms, "trace_replay inference time for background frames (per tile)");
    P_INT(detector_tiles, "tile passes per stage when the trace has no s1_tiles/s2_tiles columns");
    P_DBL(tile_merge_ms, "ASSUMED box-merge cost per extra tile");
#undef P_DBL
#undef P_INT
#undef P_U64
#undef P_BOOL
#undef P_STR
    return reg;
}

Param* find_param(const std::string& name) {
    for (auto& kv : registry())
        if (kv.first == name) return &kv.second;
    return nullptr;
}

}  // namespace

bool is_valid_mode(const std::string& mode) {
    for (const char* m : kModes)
        if (mode == m) return true;
    return false;
}

bool is_valid_scenario(const std::string& scenario) {
    for (const char* s : kScenarios)
        if (scenario == s) return true;
    return false;
}

void apply_mode_defaults(SimConfig& cfg, const std::string& mode) {
    if (!is_valid_mode(mode)) throw std::runtime_error("unknown mode: " + mode);
    cfg.mode = mode;
    // Shared defaults (theta, cooldown, detector) are NOT changed per mode,
    // so no method is tuned separately. Modes only switch components on/off.
    if (mode == "always_on") {
        cfg.security = false;
    } else if (mode == "motion_only") {
        cfg.watcher_kind = "motion";
        cfg.adaptive_trigger = false;
        cfg.security = false;
        cfg.early_exit = false;
    } else if (mode == "fixed_threshold") {
        cfg.watcher_kind = "score";
        cfg.adaptive_trigger = false;
        cfg.security = false;
        cfg.early_exit = false;
    } else if (mode == "event") {
        cfg.watcher_kind = "score";
        cfg.adaptive_trigger = true;
        cfg.security = false;
        cfg.early_exit = true;
    } else if (mode == "event_no_early_exit") {
        cfg.watcher_kind = "score";
        cfg.adaptive_trigger = true;
        cfg.security = false;
        cfg.early_exit = false;
    } else if (mode == "secure") {
        cfg.watcher_kind = "score";
        cfg.adaptive_trigger = true;
        cfg.security = true;
        cfg.security_kind = "legacy";
        cfg.early_exit = true;
    } else if (mode == "robust_event") {
        cfg.watcher_kind = "robust";
        cfg.watcher_frontend = "r2";
        cfg.security = false;
        cfg.early_exit = true;
    } else if (mode == "robust_secure") {
        cfg.watcher_kind = "robust";
        cfg.watcher_frontend = "r2";
        cfg.security = true;
        cfg.security_kind = "robust";
        cfg.early_exit = true;
    } else if (mode == "ugs_event") {
        cfg.watcher_kind = "ugs";
        cfg.watcher_frontend = "r2";
        cfg.security = false;
        cfg.early_exit = true;
    } else if (mode == "ugs_secure") {
        cfg.watcher_kind = "ugs";
        cfg.watcher_frontend = "r2";
        cfg.security = true;
        cfg.security_kind = "ugs";
        cfg.early_exit = true;
    } else if (mode == "mog2_event") {
        // Literature baseline: MOG2 background subtraction (Zivkovic 2004/2006)
        // foreground fraction >= threshold, global cooldown, no security,
        // no early exit (like the other trigger baselines).
        cfg.watcher_kind = "mog2";
        cfg.adaptive_trigger = false;
        cfg.security = false;
        cfg.early_exit = false;
    }
}

bool set_param(SimConfig& cfg, const std::string& name, const std::string& value) {
    Param* p = find_param(normalize(name));
    if (!p) return false;
    p->set(cfg, value);
    return true;
}

void load_config_file(SimConfig& cfg, const std::string& path) {
    JsonValue root = json_parse_file(path);
    if (root.type != JsonValue::OBJECT) throw std::runtime_error("config file must be a JSON object");
    for (const auto& kv : root.obj) {
        if (kv.first.empty() || kv.first[0] == '_') continue;  // comments/metadata keys
        if (kv.first == "mode") continue;                      // modes are chosen on the CLI
        if (!set_param(cfg, kv.first, kv.second.as_string()))
            throw std::runtime_error("unknown config key in " + path + ": " + kv.first);
    }
}

void parse_cli(SimConfig& cfg, int argc, char** argv, bool& help) {
    help = false;
    std::vector<std::string> args(argv + 1, argv + argc);
    std::string mode = cfg.mode;
    // Pass 1: --help, --config and --mode.
    for (size_t i = 0; i < args.size(); ++i) {
        if (args[i] == "--help" || args[i] == "-h") {
            help = true;
            return;
        }
        if (args[i] == "--config" && i + 1 < args.size()) load_config_file(cfg, args[i + 1]);
        if (args[i] == "--mode" && i + 1 < args.size()) mode = args[i + 1];
    }
    apply_mode_defaults(cfg, mode);
    // Pass 2: everything else, in order.
    for (size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto need = [&](void) -> std::string {
            if (i + 1 >= args.size()) throw std::runtime_error("missing value for " + a);
            return args[++i];
        };
        if (a == "--config" || a == "--mode") {
            ++i;
        } else if (a == "--generate-only") {
            cfg.generate_only = true;
        } else if (a == "--disable-security") {
            cfg.security = false;
            cfg.ablations.push_back("disable_security");
        } else if (a == "--disable-cooldown") {
            cfg.cooldown = false;
            cfg.ablations.push_back("disable_cooldown");
        } else if (a == "--disable-early-exit") {
            cfg.early_exit = false;
            cfg.ablations.push_back("disable_early_exit");
        } else if (a == "--disable-adaptive-trigger" || a == "--fixed-threshold") {
            cfg.adaptive_trigger = false;
            cfg.ablations.push_back(normalize(a));
        } else if (a == "--disable-replay-protection") {
            cfg.replay_protection = false;
            cfg.duplicate_protection = false;
            cfg.ablations.push_back("disable_replay_protection");
        } else if (a == "--disable-rate-limit") {
            cfg.rate_limit_enabled = false;
            cfg.ablations.push_back("disable_rate_limit");
        } else if (a == "--disable-burst-detection") {
            cfg.burst_detection = false;
            cfg.ablations.push_back("disable_burst_detection");
        } else if (a == "--disable-consistency-check") {
            cfg.consistency_check = false;
            cfg.ablations.push_back("disable_consistency_check");
        } else if (a == "--watcher-weights") {
            std::string v = need();
            std::stringstream ss(v);
            std::string tok;
            std::vector<double> w;
            while (std::getline(ss, tok, ',')) w.push_back(parse_double(tok));
            if (w.size() != 4)
                throw std::runtime_error("--watcher-weights needs 4 values: motion,visual,temporal,consistency");
            cfg.w_motion = w[0];
            cfg.w_visual = w[1];
            cfg.w_temporal = w[2];
            cfg.w_consistency = w[3];
        } else if (a == "--rate-limit" ) {
            cfg.rate_limit = static_cast<int>(parse_double(need()));
        } else if (a.rfind("--", 0) == 0) {
            std::string v = need();
            if (!set_param(cfg, a, v)) throw std::runtime_error("unknown option: " + a);
        } else {
            throw std::runtime_error("unexpected argument: " + a);
        }
    }
    if (!is_valid_scenario(cfg.scenario)) throw std::runtime_error("unknown scenario: " + cfg.scenario);
    if (cfg.debug_random_block_prob > 0.0) cfg.ablations.push_back("DEBUG_random_block");
}

std::string config_to_json(const SimConfig& cfg) {
    std::string out = "{\n";
    for (const auto& kv : registry()) out += "  \"" + kv.first + "\": " + kv.second.json(cfg) + ",\n";
    out += "  \"ablations\": [";
    for (size_t i = 0; i < cfg.ablations.size(); ++i)
        out += (i ? ", \"" : "\"") + cfg.ablations[i] + "\"";
    out += "]\n}\n";
    return out;
}

std::string cli_help() {
    std::string h =
        "edge_sim - secure dual-core event-triggered object detection simulator\n\n"
        "Usage: edge_sim [--config FILE] [--mode MODE] [options]\n\n"
        "Modes: always_on motion_only fixed_threshold event event_no_early_exit secure\n"
        "       robust_event robust_secure mog2_event (R2), ugs_event ugs_secure (R3)\n"
        "Scenarios: quiet normal busy burst noisy trigger_spam replay mixed\n\n"
        "Flags without value:\n"
        "  --generate-only --disable-security --disable-cooldown --disable-early-exit\n"
        "  --disable-adaptive-trigger --fixed-threshold --disable-replay-protection\n"
        "  --disable-rate-limit --disable-burst-detection --disable-consistency-check\n"
        "  --watcher-weights m,v,t,c\n\n"
        "Parameters (--name value; booleans take on|off):\n";
    for (const auto& kv : registry()) {
        std::string flag = kv.first;
        for (char& c : flag)
            if (c == '_') c = '-';
        h += "  --" + flag + "  " + kv.second.help + "\n";
    }
    return h;
}

}  // namespace sim
