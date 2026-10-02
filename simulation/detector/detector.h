// M7 object-detection workload model.
//
// The simulator does not run a CNN. A detector backend produces, for each
// frame the M7 processes, the stage-1 output, an optional stage-2 (second
// pass) output, and postprocessing time:
//
//   synthetic_distribution: seeded parametric distributions (simulation-only
//       assumptions, see docs/SIMULATION_METHOD.md).
//   trace_replay: per-event predictions read from a CSV produced offline by a
//       real detector (schema in data/detector_traces/README.md).
//
// Draws are keyed by (seed, event_id, stage), so an event processed in two
// different modes receives exactly the same detector outcome.
#pragma once

#include <map>
#include <memory>
#include <string>

#include "config/sim_config.h"
#include "core/types.h"

namespace sim {

struct DetectorInput {
    uint64_t key = 0;          // event_id, or a background-cycle id
    bool background = false;   // always_on frame with no workload observation
    bool frame_has_object = false;
    int frame_class = CLS_NONE;
    double visual_score = 0.0;
    double noise_score = 0.0;
};

struct StageOutput {
    double confidence = 0.0;
    int predicted_class = CLS_NONE;
    int num_boxes = 0;
    double latency_ms = 0.0;
    bool available = true;   // false when a trace has no second-pass data
};

class DetectorBackend {
public:
    virtual ~DetectorBackend() = default;
    virtual StageOutput stage1(const DetectorInput& in) = 0;
    virtual StageOutput stage2(const DetectorInput& in, const StageOutput& s1) = 0;
    virtual double postprocess_ms(const DetectorInput& in, const StageOutput& final_out) = 0;
    virtual std::string name() const = 0;
};

std::unique_ptr<DetectorBackend> make_detector(const SimConfig& cfg);

}  // namespace sim
