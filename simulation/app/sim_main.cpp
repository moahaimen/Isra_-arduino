// edge_sim: command-line entry point of the research simulator.
//
// Typical use:
//   edge_sim --scenario normal --seed 1 --seconds 600 --save-workload wl.jsonl --generate-only
//   edge_sim --config config/default_config.json --mode secure --workload wl.jsonl
//            --out-dir results/run1
#include <sys/stat.h>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>

#include "config/sim_config.h"
#include "core/json.h"
#include "core/simulator.h"
#include "energy/energy_model.h"
#include "workload/workload.h"

using namespace sim;

namespace {

void make_dirs(const std::string& path) {
    std::string cur;
    for (size_t i = 0; i < path.size(); ++i) {
        cur += path[i];
        if (path[i] == '/' || i + 1 == path.size()) mkdir(cur.c_str(), 0755);
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        SimConfig cfg;
        bool help = false;
        parse_cli(cfg, argc, argv, help);
        if (help) {
            std::cout << cli_help();
            return 0;
        }

        Workload wl;
        std::string wl_hash;
        if (!cfg.workload.empty()) {
            wl = load_workload(cfg.workload);
            // The horizon comes from the workload metadata when available.
            const std::string meta = cfg.workload + ".meta.json";
            std::ifstream mf(meta);
            if (mf.good()) {
                JsonValue m = json_parse_file(meta);
                const double meta_seconds = m.at("seconds").as_number();
                cfg.seconds = meta_seconds;
                cfg.seed = static_cast<uint64_t>(m.at("seed").as_number());
                cfg.scenario = m.at("scenario").as_string();
            }
            if (wl.seconds > cfg.seconds + 1e-9)
                throw std::runtime_error("workload extends beyond --seconds");
            wl.seconds = cfg.seconds;
            wl.seed = cfg.seed;
            if (wl.scenario.empty()) wl.scenario = cfg.scenario;
            wl_hash = file_hash_hex(cfg.workload);
        } else {
            wl = generate_workload(cfg);
            if (!cfg.save_workload.empty()) {
                save_workload(wl, cfg.save_workload, cfg);
                wl_hash = file_hash_hex(cfg.save_workload);
            } else {
                // Hash of the canonical serialisation, identical to the file hash.
                uint64_t h = 0xcbf29ce484222325ULL;
                for (const auto& e : wl.events) {
                    const std::string line = workload_event_to_jsonl(e) + "\n";
                    for (unsigned char c : line) {
                        h ^= c;
                        h *= 0x100000001b3ULL;
                    }
                }
                wl_hash = hex64(h);
            }
        }
        if (cfg.generate_only) {
            std::cout << "{\"generated_events\": " << wl.events.size() << ", \"workload_hash_fnv1a64\": \"" << wl_hash
                      << "\"}\n";
            return 0;
        }

        PowerModel pm = load_power_model(cfg.power_model);
        if (!cfg.out_dir.empty()) {
            make_dirs(cfg.out_dir);
            std::ofstream c(cfg.out_dir + "/config.json");
            c << config_to_json(cfg);
        }
        auto simulator = std::make_unique<Simulator>(cfg, wl, pm);
        simulator->run();
        if (!cfg.out_dir.empty()) simulator->write_outputs(cfg.out_dir, wl_hash);
        const RunSummary& s = simulator->summary();
        std::printf(
            "{\"mode\": \"%s\", \"scenario\": \"%s\", \"seed\": %llu, \"observations\": %llu, \"triggers\": %llu, "
            "\"security_block\": %llu, \"wakes\": %llu, \"results\": %llu, \"duty_cycle\": %.6f, "
            "\"energy_mJ\": %.3f, \"workload_hash_fnv1a64\": \"%s\"}\n",
            cfg.mode.c_str(), wl.scenario.c_str(), static_cast<unsigned long long>(cfg.seed),
            static_cast<unsigned long long>(s.observations), static_cast<unsigned long long>(s.triggers),
            static_cast<unsigned long long>(s.security_block), static_cast<unsigned long long>(s.wakes),
            static_cast<unsigned long long>(s.results), s.m7_active_ms / (cfg.seconds * 1000.0),
            simulator->energy_mj(), wl_hash.c_str());
        return 0;
    } catch (const std::exception& ex) {
        std::fprintf(stderr, "edge_sim error: %s\n", ex.what());
        return 2;
    }
}
