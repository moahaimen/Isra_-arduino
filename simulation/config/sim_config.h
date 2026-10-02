// Simulator configuration.
//
// Every tunable parameter lives in SimConfig and is registered once in
// sim_config.cpp under a single name. That name is used for the CLI flag
// (--trigger-threshold), for config/default_config.json keys
// (trigger_threshold) and for the resolved config.json written with every
// run, so no parameter can silently differ between those three places.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace sim {

struct SimConfig {
    // --- run identity ---------------------------------------------------
    std::string mode = "secure";       // always_on|motion_only|fixed_threshold|event|event_no_early_exit|secure
                                       // R2: robust_event|robust_secure|mog2_event
    std::string scenario = "normal";   // quiet|normal|busy|burst|noisy|trigger_spam|replay|mixed
    uint64_t seed = 1;
    double seconds = 600.0;
    std::string workload;              // replay this workload JSONL instead of generating
    std::string save_workload;         // write the generated workload here
    std::string out_dir;               // per-run output directory
    std::string power_model = "config/power_model.json";
    std::string log_level = "full";    // full|decisions|none (JSONL event log verbosity)
    bool generate_only = false;

    // --- workload generator ----------------------------------------------
    double attack_intensity = 1.0;     // multiplies attack-session arrival rate and in-session attack rate
    double arrival_scale = 1.0;        // multiplies legitimate episode arrival rates
    double spam_sophistication = 0.3;  // fraction of spam triggers that mimic consistent sensors
    double replay_perturb_prob = 0.3;  // fraction of replays perturbed to defeat exact hashing

    // --- M4 watcher --------------------------------------------------------
    std::string watcher_kind = "score";  // score|motion (R1); robust|mog2 (R2)
    std::string watcher_frontend = "basic";  // basic|r2 (gain-compensated, R2 workloads only)
    double w_motion = 0.30, w_visual = 0.35, w_temporal = 0.20, w_consistency = 0.15;
    double trigger_threshold = 0.55;
    double motion_threshold = 0.55;
    double cooldown_ms = 1500.0;
    bool cooldown = true;
    bool adaptive_trigger = true;
    double adaptive_gain = 0.5;
    double adaptive_noise_ref = 0.15;
    double adaptive_ewma_alpha = 0.05;
    double m4_process_ms = 1.0;
    // R2 robust watcher (simulation/watcher/robust_watcher.h)
    int robust_bg_window = 64;
    int robust_bg_min = 8;
    double robust_z_on = 4.0;
    double robust_z_off = 2.0;
    double robust_theta_min = 0.20;
    double robust_theta_max = 0.55;
    double robust_sigma_floor = 0.02;
    int robust_persist_k = 2;
    int robust_release_k = 3;
    bool robust_threshold = true;
    bool content_cooldown = true;
    double content_cooldown_ms = 1000.0;
    double content_overlap_thr = 0.3;
    double region_ttl_ms = 3000.0;
    // MOG2 background-subtraction trigger (literature baseline)
    double mog2_threshold = 0.02;

    // --- security gate -------------------------------------------------------
    bool security = false;
    std::string security_kind = "legacy";  // legacy (R1 gate) | robust (R2 gate)
    bool rate_limit_enabled = true;
    int rate_limit = 20;
    double rate_window_ms = 60000.0;
    bool replay_protection = true;
    double replay_window_ms = 600000.0;
    double replay_feature_eps = 0.01;
    bool duplicate_protection = true;
    double duplicate_window_ms = 2000.0;
    bool burst_detection = true;
    int burst_threshold = 10;
    double burst_window_ms = 5000.0;
    bool consistency_check = true;
    double consistency_threshold = 0.5;
    int security_history = 512;
    double security_process_ms = 0.4;
    double debug_random_block_prob = 0.0;  // DEBUG ONLY: legacy probability blocking
    // R2 robust gate (simulation/security/robust_gate.h)
    bool rg_consistency = true;
    double rg_consistency_threshold = 0.3;
    bool rg_replay = true;
    double rg_replay_window_ms = 60000.0;
    double rg_replay_min_age_ms = 2000.0;
    double rg_fg_jaccard_thr = 0.80;
    int rg_dhash_max = 32;
    int rg_fg_min = 12;
    int rg_history = 256;
    bool rg_content_bucket = true;
    double rg_content_capacity = 3.0;
    double rg_content_refill_per_s = 0.5;
    double rg_content_ttl_ms = 10000.0;
    bool rg_global_bucket = true;
    double rg_global_capacity = 10.0;
    double rg_global_refill_per_s = 1.0;
    bool rg_emergency = true;
    double rg_emergency_capacity = 3.0;
    double rg_emergency_refill_per_s = 0.1;
    double rg_z_emergency = 6.0;

    // --- RPC / inter-core communication ---------------------------------------
    double rpc_latency_ms = 0.5;
    double rpc_jitter_ms = 0.2;
    double rpc_loss = 0.0;
    int rpc_queue_capacity = 8;

    // --- detector workload model -------------------------------------------------
    std::string detector_backend = "synthetic_distribution";  // synthetic_distribution|trace_replay
    std::string detector_trace;
    std::string trace_timing = "trace";     // trace: latencies from the trace; simulated: M7 timing model
    double inference_ms = 140.0;            // median stage-1 inference latency
    double inference_sigma = 0.08;          // log-normal sigma of inference latency
    double second_pass_cost_ms = 110.0;     // median stage-2 latency
    double postprocess_base_ms = 6.0;
    double postprocess_per_box_ms = 1.5;
    double detection_threshold = 0.5;
    bool early_exit = true;
    double early_exit_threshold = 0.80;
    double early_exit_low_threshold = 0.15;
    double m7_wakeup_ms = 3.0;
    double m7_linger_ms = 0.0;
    double trace_background_inference_ms = 140.0;

    // --- derived/meta -------------------------------------------------------------
    std::vector<std::string> ablations;  // recorded for metadata only
};

// Apply mode semantics (which components are active). Called before CLI/JSON
// overrides so that explicit ablation flags win.
void apply_mode_defaults(SimConfig& cfg, const std::string& mode);

// Set a parameter by its registered name (dashes or underscores).
// Returns false if the name is unknown.
bool set_param(SimConfig& cfg, const std::string& name, const std::string& value);

// Load a flat JSON object of parameter overrides.
void load_config_file(SimConfig& cfg, const std::string& path);

// Parse argv. Throws std::runtime_error on bad input. Sets help=true for --help.
void parse_cli(SimConfig& cfg, int argc, char** argv, bool& help);

std::string config_to_json(const SimConfig& cfg);
std::string cli_help();
bool is_valid_mode(const std::string& mode);
bool is_valid_scenario(const std::string& scenario);

}  // namespace sim
