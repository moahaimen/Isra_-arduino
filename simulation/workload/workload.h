// Shared ground-truth workload traces.
//
// A workload is generated once per (scenario, seed, duration, generator
// parameters) and then replayed by every operating mode. Workload files are
// JSONL, one observation per line, with a fixed key order and fixed numeric
// precision so that repeated generation is byte-identical.
#pragma once

#include <string>

#include "config/sim_config.h"
#include "core/types.h"

namespace sim {

constexpr const char* kWorkloadGeneratorVersion = "wlgen-1.0";

struct ScenarioParams {
    std::string name;
    // Legitimate episode process: two-state Markov-modulated Poisson process.
    double rate_calm = 0.0;     // episodes per second in the CALM state
    double rate_active = 0.0;   // episodes per second in the ACTIVE state
    double calm_to_active = 0.0;  // state switching rates (per second)
    double active_to_calm = 0.0;
    double p_object = 0.55, p_benign = 0.30, p_noise = 0.15;  // episode type mix
    double noise_base = 0.12;   // background sensor-noise level
    // Legitimate burst process (crowds, traffic platoons).
    double burst_rate = 0.0;    // bursts per second
    int burst_min = 0, burst_max = 0;
    double burst_span_s = 0.0;
    // Attack processes (rates already multiplied by attack intensity).
    double spam_session_rate = 0.0;   // spam sessions per second
    double spam_session_mean_s = 60.0;
    double spam_rate = 3.0;           // fake triggers per second inside a session
    double replay_session_rate = 0.0; // replay sessions per second
};

ScenarioParams scenario_params(const std::string& scenario, const SimConfig& cfg);
std::string scenario_params_json(const ScenarioParams& p);

Workload generate_workload(const SimConfig& cfg);
void save_workload(const Workload& wl, const std::string& path, const SimConfig& cfg);
Workload load_workload(const std::string& path);
std::string workload_event_to_jsonl(const WorkloadEvent& e);

// FNV-1a 64-bit hash of a file's bytes, as 16 hex digits.
std::string file_hash_hex(const std::string& path);
std::string hex64(uint64_t v);

}  // namespace sim
