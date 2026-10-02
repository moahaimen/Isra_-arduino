// Discrete-event simulator of the dual-core event-triggered detection pipeline.
//
//   M4 watcher -> trigger decision -> security gate -> RPC transmission
//   -> M7 wake -> detector stage 1 -> early exit | second pass
//   -> postprocessing -> result (RPC back to M4) -> M7 sleep
//
// Simulated time is in milliseconds (double). Events are processed in time
// order with a deterministic tie-break (insertion sequence), so a run is a
// pure function of (configuration, workload).
#pragma once

#include <cstdint>
#include <deque>
#include <memory>
#include <queue>
#include <string>
#include <vector>

#include "communication/rpc_model.h"
#include "config/sim_config.h"
#include "core/types.h"
#include "detector/detector.h"
#include "energy/energy_model.h"
#include "logging/event_log.h"
#include "security/robust_gate.h"
#include "security/security_gate.h"
#include "watcher/robust_watcher.h"
#include "watcher/watcher.h"

namespace sim {

// Outcome of one workload observation in one run.
struct ObsRecord {
    // Watcher
    bool m4_evaluated = false;
    double m4_start_ms = -1.0;
    double decision_ms = -1.0;
    double score = 0.0;
    double threshold = 0.0;
    bool raw_positive = false;
    bool triggered = false;
    std::string suppress_reason = "NONE";
    double z = 0.0;           // robust watcher z-score (R2)
    bool novel = false;       // robust watcher: trigger opened a new content region
    // Security
    bool sec_evaluated = false;
    bool sec_accept = false;
    std::string sec_reason = "NONE";
    double sec_done_ms = -1.0;
    double consistency_metric = -1.0;
    // RPC
    std::string rpc_status = "none";  // none|delivered|lost|queue_full
    double rpc_send_ms = -1.0;
    double rpc_channel_wait_ms = -1.0;
    double rpc_tx_ms = -1.0;
    double rpc_receive_ms = -1.0;
    double enqueue_ms = -1.0;
    double dequeue_ms = -1.0;
    double queue_delay_ms = -1.0;   // waiting for the M7 to become free (excludes wake-up)
    double wake_wait_ms = -1.0;     // part of the M7-side wait spent waking the M7
    bool caused_wake = false;
    // M7 detector
    bool processed = false;     // detector finished (RESULT produced)
    bool started = false;       // detector started
    double detect_start_ms = -1.0;
    double s1_conf = -1.0;
    int s1_class = 0;
    double s1_ms = 0.0;
    bool early_exit = false;
    bool second_pass = false;
    double s2_conf = -1.0;
    int s2_class = 0;
    double s2_ms = 0.0;
    double post_ms = 0.0;
    double final_conf = -1.0;
    int final_class = 0;
    int num_boxes = 0;
    bool detected = false;
    double result_m7_ms = -1.0;
    double result_delivered_ms = -1.0;
    double result_rpc_ms = -1.0;
};

struct RunSummary {
    uint64_t observations = 0;
    uint64_t watcher_evaluations = 0;
    uint64_t raw_positives = 0;
    uint64_t triggers = 0;
    uint64_t suppressed_cooldown = 0;
    uint64_t security_accept = 0;
    uint64_t security_block = 0;
    uint64_t rpc_sent = 0;
    uint64_t rpc_lost = 0;
    uint64_t rpc_queue_full = 0;
    uint64_t wakes = 0;
    uint64_t sleeps = 0;
    uint64_t results = 0;
    uint64_t results_delivered = 0;
    uint64_t early_exits = 0;
    uint64_t second_passes = 0;
    uint64_t bg_cycles = 0;
    uint64_t bg_detections = 0;
    uint64_t ao_missed_observations = 0;
    double m7_active_ms = 0.0;
};

class Simulator {
public:
    Simulator(const SimConfig& cfg, const Workload& wl, const PowerModel& pm);
    void run();
    void write_outputs(const std::string& out_dir, const std::string& workload_hash) const;

    const std::vector<ObsRecord>& records() const { return rec_; }
    const RunSummary& summary() const { return sum_; }
    double state_time_ms(int core, int state) const;  // core 4 or 7
    double energy_mj() const;

private:
    enum EvType {
        OBS_ARRIVAL,
        M4_WATCH_DONE,
        M4_SEC_DONE,
        M4_TX_DONE,
        M7_WAKE_DONE,
        M7_STAGE1_DONE,
        M7_STAGE2_DONE,
        M7_POST_DONE,
        RESULT_ARRIVE_M4,
        M7_LINGER_END,
        AO_CYCLE,
    };
    struct Ev {
        double t;
        uint64_t seq;
        int type;
        int64_t a;
        bool operator>(const Ev& o) const { return t != o.t ? t > o.t : seq > o.seq; }
    };
    struct Job {
        int64_t idx = -1;  // workload index, -1 for an always_on background frame
        uint64_t bg_id = 0;
        DetectorInput in;
        StageOutput s1, s2;
        bool did_s2 = false;
        StageOutput final_out;
    };

    const SimConfig& cfg_;
    const Workload& wl_;
    PowerModel pm_;
    double T_;
    bool always_on_;
    std::priority_queue<Ev, std::vector<Ev>, std::greater<Ev>> q_;
    uint64_t seq_ = 0;
    EventLog log_;
    std::string log_path_;

    Watcher watcher_;
    SecurityGate<2048> gate_;
    RobustWatcher rwatcher_;
    RobustGate<512> rgate_;
    bool robust_watcher_;
    bool robust_gate_;
    RpcChannel rpc_;
    std::unique_ptr<DetectorBackend> det_;
    CoreStateTracker m4_, m7_;

    std::vector<ObsRecord> rec_;
    RunSummary sum_;

    // M4 serial processing
    std::deque<int64_t> m4_queue_;
    bool m4_busy_ = false;
    // M7
    struct Pending {
        int64_t idx;
        double enq_ms;
    };
    std::deque<Pending> m7_queue_;
    bool m7_busy_ = false;  // executing a job (or waking up)
    Job job_;
    double wake_start_ms_ = -1.0;
    double wake_done_ms_ = -1.0;
    uint64_t linger_gen_ = 0;
    std::vector<std::pair<double, double>> wake_intervals_;
    std::vector<bool> wake_forced_;
    // always_on frame capture
    size_t ao_next_ = 0;
    std::deque<int64_t> ao_pending_;
    uint64_t bg_counter_ = 0;
    double bg_noise_ = 0.12;

    void push(double t, int type, int64_t a);
    void log_begin_event(double t, const char* ev, int64_t idx);

    void on_obs_arrival(double t, int64_t idx);
    void m4_start_next(double t);
    void on_watch_done(double t, int64_t idx);
    void on_sec_done(double t, int64_t idx);
    void send_request(double t, int64_t idx);
    void on_tx_done(double t, int64_t idx);
    void m4_finish(double t, int64_t idx);

    void m7_wake(double t, int64_t cause_idx);
    void m7_sleep(double t, bool forced);
    void m7_dequeue_and_start(double t);
    void start_job(double t, const Job& job);
    void on_stage1_done(double t);
    void on_stage2_done(double t);
    void start_post(double t);
    void on_post_done(double t);
    void m7_after_job(double t);
    void on_result_arrive(double t, int64_t idx);
    void on_ao_cycle(double t);

    SecurityFrame frame_of(int64_t idx) const;
    RobustFrame robust_frame_of(int64_t idx) const;
};

WatcherParams watcher_params_from(const SimConfig& cfg);
SecurityParams security_params_from(const SimConfig& cfg);
RobustWatcherParams robust_watcher_params_from(const SimConfig& cfg);
RobustGateParams robust_gate_params_from(const SimConfig& cfg);

}  // namespace sim
