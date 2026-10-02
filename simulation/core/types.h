// Core data types shared by every simulator component.
//
// The split between Observable and GroundTruth is deliberate and is the main
// structural guard against label leakage: the M4 watcher and the security
// gate only ever receive an Observable. Ground-truth labels travel in a
// separate struct that only the logger and the evaluation scripts read.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace sim {

// Object classes. Index 0 means "no object / no detection".
enum ObjectClass : int { CLS_NONE = 0, CLS_PERSON = 1, CLS_VEHICLE = 2, CLS_ANIMAL = 3, CLS_PACKAGE = 4 };
constexpr int kNumObjectClasses = 4;
const char* class_name(int cls);
int class_from_name(const std::string& name);

// What the always-on M4 watcher can sense about one candidate observation.
struct Observable {
    uint64_t event_id = 0;
    double timestamp_ms = 0.0;   // onset of the observation
    double duration_ms = 0.0;    // how long the stimulus/frame stays visible
    double motion_score = 0.0;            // PIR / frame-difference motion estimate
    double visual_score = 0.0;            // low-resolution visual saliency
    double temporal_change_score = 0.0;   // multi-frame temporal change
    double sensor_consistency_score = 0.0;  // agreement between sensing channels
    double noise_score = 0.0;             // estimated sensor noise level
    uint64_t content_signature = 0;       // perceptual hash of the captured frame

    // --- R2 real-frame features (present when has_r2; see
    // scripts/r2/frame_features.py for the exact equations). All are
    // computed by the M4 from the displayed low-resolution frame only.
    bool has_r2 = false;
    double edge_change_score = 0.0;  // scale-invariant edge-map change
    double r2_motion = 0.0;          // gain-compensated frame-difference fraction
    double r2_temporal = 0.0;        // gain-compensated background deviation
    double r2_visual = 0.0;          // gain-compensated cell activity
    double r2_consistency = 0.0;     // agreement of compensated motion and edge change
    double mog2_fg = 0.0;            // MOG2 foreground fraction (literature baseline input)
    uint64_t motion_cells = 0;       // 12 x 4 cell motion bitmask (bit = cy*12 + cx)
    uint64_t fp256[4] = {0, 0, 0, 0};  // 256-bit difference hash of a 17 x 16 thumbnail
    uint64_t fg768[12] = {};         // 48 x 16 foreground mask (gain-compensated)
    int fg_count = 0;                // set bits in fg768
};

// Labels known only to the workload generator and the evaluator.
struct GroundTruth {
    std::string scenario;
    int64_t episode_id = -1;
    bool is_legitimate = true;
    bool object_present = false;        // a real object is physically present
    int object_class = CLS_NONE;
    std::string attack_type = "none";   // none | trigger_spam | replay
    int64_t replay_id = -1;             // event_id of the replayed original
    int64_t burst_id = -1;
    std::string episode_type;           // object | benign_motion | noise | attack
    std::string ground_truth_action;    // detect | ignore | block
    // Physical frame content seen by the camera. Used ONLY by the detector
    // workload model (it simulates the physics of what the camera images);
    // never by the watcher or the security gate.
    bool frame_has_object = false;
    int frame_object_class = CLS_NONE;
};

struct WorkloadEvent {
    Observable obs;
    GroundTruth gt;
};

struct Workload {
    std::string scenario;
    uint64_t seed = 0;
    double seconds = 0.0;
    std::vector<WorkloadEvent> events;
};

}  // namespace sim
