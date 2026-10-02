// M4 watcher decision model.
//
// Header-only and free of heap allocation so the same logic can be compiled
// into the Cortex-M4 firmware (see firmware/). It only ever sees observable
// features, never ground-truth labels.
//
//   S_t = w_m*motion + w_v*visual + w_t*temporal + w_c*consistency
//   theta_t = theta + gain * max(0, ewma(noise) - noise_ref)   (adaptive)
//   theta_t = theta                                             (fixed)
//   raw_t = S_t >= theta_t
//   trigger_t = raw_t and (t - t_last_trigger >= cooldown)
//
// The motion-only baseline replaces S_t by motion_score and theta by the
// motion threshold.
#pragma once

namespace sim {

enum WatcherSuppress { WS_NONE = 0, WS_BELOW_THRESHOLD = 1, WS_COOLDOWN = 2 };

struct WatcherParams {
    bool motion_only = false;
    double w_motion = 0.30, w_visual = 0.35, w_temporal = 0.20, w_consistency = 0.15;
    double theta = 0.55;
    double motion_threshold = 0.55;
    bool use_cooldown = true;
    double cooldown_ms = 1500.0;
    bool adaptive = true;
    double adaptive_gain = 0.5;
    double noise_ref = 0.15;
    double ewma_alpha = 0.05;
};

struct WatcherFeatures {
    double motion, visual, temporal, consistency, noise;
};

struct WatcherDecision {
    double score = 0.0;
    double threshold = 0.0;
    bool raw_positive = false;  // score >= threshold
    bool trigger = false;       // raw_positive and not in cooldown
    int suppress = WS_NONE;
};

class Watcher {
public:
    explicit Watcher(const WatcherParams& p) : p_(p), noise_ewma_(p.noise_ref) {}

    WatcherDecision evaluate(double t_ms, const WatcherFeatures& f) {
        WatcherDecision d;
        // The noise estimate is updated before the decision; it uses only
        // the observable noise feature of past and current observations.
        noise_ewma_ = p_.ewma_alpha * f.noise + (1.0 - p_.ewma_alpha) * noise_ewma_;
        if (p_.motion_only) {
            d.score = f.motion;
            d.threshold = p_.motion_threshold;
        } else {
            d.score = p_.w_motion * f.motion + p_.w_visual * f.visual + p_.w_temporal * f.temporal +
                      p_.w_consistency * f.consistency;
            d.threshold = p_.theta;
            if (p_.adaptive) {
                const double excess = noise_ewma_ - p_.noise_ref;
                if (excess > 0.0) d.threshold += p_.adaptive_gain * excess;
            }
        }
        d.raw_positive = d.score >= d.threshold;
        if (!d.raw_positive) {
            d.suppress = WS_BELOW_THRESHOLD;
            return d;
        }
        if (p_.use_cooldown && has_triggered_ && (t_ms - last_trigger_ms_) < p_.cooldown_ms) {
            d.suppress = WS_COOLDOWN;
            return d;
        }
        d.trigger = true;
        has_triggered_ = true;
        last_trigger_ms_ = t_ms;
        return d;
    }

    double noise_estimate() const { return noise_ewma_; }

private:
    WatcherParams p_;
    double noise_ewma_;
    bool has_triggered_ = false;
    double last_trigger_ms_ = 0.0;
};

}  // namespace sim
