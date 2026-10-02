#include "energy/energy_model.h"

#include <stdexcept>

#include "core/json.h"

namespace sim {

namespace {
const char* kNames[NUM_POWER_STATES] = {
    "M4_IDLE",        "M4_MONITOR",   "M4_PROCESS",     "SECURITY_PROCESSING", "RPC_COMMUNICATION", "M7_SLEEP",
    "M7_WAKEUP",      "M7_INFERENCE", "M7_SECOND_PASS", "M7_POSTPROCESS",      "M7_IDLE_AWAKE",
};
}  // namespace

const char* power_state_name(int s) { return (s >= 0 && s < NUM_POWER_STATES) ? kNames[s] : "UNKNOWN"; }

bool is_m4_state(int s) { return s <= RPC_COMMUNICATION; }

PowerModel load_power_model(const std::string& path) {
    JsonValue root = json_parse_file(path);
    PowerModel pm;
    pm.units = root.at("units").as_string();
    if (pm.units != "mW") throw std::runtime_error("power model units must be mW");
    pm.source = root.at("source").as_string();
    pm.calibrated = root.has("calibrated") && root.at("calibrated").as_bool();
    const JsonValue& states = root.at("states");
    for (int s = 0; s < NUM_POWER_STATES; ++s) {
        const JsonValue& st = states.at(kNames[s]);
        pm.power_mw[s] = st.at("power_mW").as_number();
        if (pm.power_mw[s] < 0.0) throw std::runtime_error(std::string("negative power for ") + kNames[s]);
    }
    return pm;
}

}  // namespace sim
