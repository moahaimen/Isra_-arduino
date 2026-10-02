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

const char* kModes[] = {"always_on", "motion_only", "fixed_threshold", "event", "event_no_early_exit", "secure"};
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
    P_STR(watcher_kind, "watcher decision rule: score|motion");
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
    P_BOOL(security, "enable the security gate");
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
    P_DBL(rpc_latency_ms, "RPC base transmission latency");
    P_DBL(rpc_jitter_ms, "RPC jitter scale (half-normal)");
    P_DBL(rpc_loss, "RPC request loss probability");
    P_INT(rpc_queue_capacity, "M7 request queue capacity");
    P_STR(detector_backend, "synthetic_distribution|trace_replay");
    P_STR(detector_trace, "detector trace CSV for trace_replay");
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
    P_DBL(trace_background_inference_ms, "trace_replay inference time for background frames");
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
        cfg.early_exit = true;
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
