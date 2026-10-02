// State-based modeled energy.
//
// Each core is in exactly one power state at any time. The tracker integrates
// the time spent in each state over [0, T]; modeled energy is
//   E_s = P_s * T_s,   E_total = sum_s E_s
// with P_s taken from config/power_model.json (mW). Time is in ms, so
// E[mJ] = P[mW] * T[ms] / 1000.
//
// All power values are SIMULATION ASSUMPTIONS until calibrated on hardware
// (docs/ENERGY_MODEL.md, docs/HARDWARE_VALIDATION_PLAN.md).
#pragma once

#include <map>
#include <string>
#include <vector>

namespace sim {

enum PowerState {
    M4_IDLE = 0,
    M4_MONITOR,
    M4_PROCESS,
    SECURITY_PROCESSING,
    RPC_COMMUNICATION,
    M7_SLEEP,
    M7_WAKEUP,
    M7_INFERENCE,
    M7_SECOND_PASS,
    M7_POSTPROCESS,
    M7_IDLE_AWAKE,
    NUM_POWER_STATES
};

const char* power_state_name(int s);
bool is_m4_state(int s);

struct PowerModel {
    std::string units = "mW";
    std::string source;
    bool calibrated = false;
    double power_mw[NUM_POWER_STATES] = {};
};

PowerModel load_power_model(const std::string& path);

class CoreStateTracker {
public:
    CoreStateTracker() = default;
    CoreStateTracker(int initial_state, double t0) : state_(initial_state), since_(t0) {}

    void set(double t, int state) {
        if (t > since_) time_ms_[state_] += t - since_;
        if (t > since_) since_ = t;
        state_ = state;
    }
    void finalize(double t_end) {
        if (t_end > since_) time_ms_[state_] += t_end - since_;
        since_ = t_end;
    }
    int state() const { return state_; }
    double time_in(int s) const { return time_ms_[s]; }

private:
    int state_ = M4_IDLE;
    double since_ = 0.0;
    double time_ms_[NUM_POWER_STATES] = {};
};

}  // namespace sim
