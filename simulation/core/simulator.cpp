#include "core/simulator.h"

#include <cstdio>
#include <fstream>
#include <stdexcept>

#include "core/rng.h"
#include "workload/workload.h"

namespace sim {

WatcherParams watcher_params_from(const SimConfig& c) {
    WatcherParams p;
    p.motion_only = (c.watcher_kind == "motion");
    p.w_motion = c.w_motion;
    p.w_visual = c.w_visual;
    p.w_temporal = c.w_temporal;
    p.w_consistency = c.w_consistency;
    p.theta = c.trigger_threshold;
    p.motion_threshold = c.motion_threshold;
    p.use_cooldown = c.cooldown;
    p.cooldown_ms = c.cooldown_ms;
    p.adaptive = c.adaptive_trigger;
    p.adaptive_gain = c.adaptive_gain;
    p.noise_ref = c.adaptive_noise_ref;
    p.ewma_alpha = c.adaptive_ewma_alpha;
    return p;
}

SecurityParams security_params_from(const SimConfig& c) {
    SecurityParams p;
    p.rate_limit_on = c.rate_limit_enabled;
    p.rate_limit = c.rate_limit;
    p.rate_window_ms = c.rate_window_ms;
    p.replay_on = c.replay_protection;
    p.replay_window_ms = c.replay_window_ms;
    p.replay_feature_eps = c.replay_feature_eps;
    p.duplicate_on = c.duplicate_protection;
    p.duplicate_window_ms = c.duplicate_window_ms;
    p.burst_on = c.burst_detection;
    p.burst_threshold = c.burst_threshold;
    p.burst_window_ms = c.burst_window_ms;
    p.consistency_on = c.consistency_check;
    p.consistency_threshold = c.consistency_threshold;
    p.history_capacity = c.security_history;
    return p;
}

Simulator::Simulator(const SimConfig& cfg, const Workload& wl, const PowerModel& pm)
    : cfg_(cfg),
      wl_(wl),
      pm_(pm),
      T_(cfg.seconds * 1000.0),
      always_on_(cfg.mode == "always_on"),
      watcher_(watcher_params_from(cfg)),
      gate_(security_params_from(cfg)),
      rpc_(cfg),
      det_(make_detector(cfg)),
      m4_(always_on_ ? M4_IDLE : M4_MONITOR, 0.0),
      m7_(M7_SLEEP, 0.0) {
    rec_.resize(wl.events.size());
    bg_noise_ = is_valid_scenario(wl.scenario) ? scenario_params(wl.scenario, cfg).noise_base : 0.12;
    for (size_t i = 0; i < wl.events.size(); ++i) {
        const auto& o = wl.events[i].obs;
        if (o.timestamp_ms < 0.0 || o.timestamp_ms >= T_)
            throw std::runtime_error("workload event outside simulation horizon: event_id " +
                                     std::to_string(o.event_id));
    }
    if (!cfg.out_dir.empty()) {
        log_path_ = cfg.out_dir + "/events.jsonl";
        LogLevel lvl = cfg.log_level == "none" ? LOG_NONE : (cfg.log_level == "decisions" ? LOG_DECISIONS : LOG_FULL);
        if (!log_.open(log_path_, lvl)) throw std::runtime_error("cannot open event log: " + log_path_);
    }
}

void Simulator::push(double t, int type, int64_t a) { q_.push(Ev{t, seq_++, type, a}); }

SecurityFrame Simulator::frame_of(int64_t idx) const {
    const Observable& o = wl_.events[static_cast<size_t>(idx)].obs;
    return SecurityFrame{o.timestamp_ms, o.motion_score, o.visual_score, o.temporal_change_score,
                         o.sensor_consistency_score, o.content_signature};
}

void Simulator::log_begin_event(double t, const char* ev, int64_t idx) {
    log_.begin(t, ev).kv("event_id", wl_.events[static_cast<size_t>(idx)].obs.event_id);
}

void Simulator::run() {
    if (log_.enabled(LOG_DECISIONS)) {
        log_.begin(0.0, "SIM_START")
            .kv("mode", cfg_.mode)
            .kv("scenario", wl_.scenario)
            .kv("seed", cfg_.seed)
            .kvf("seconds", cfg_.seconds, 3)
            .kv("detector_backend", det_->name())
            .kv("observations", static_cast<uint64_t>(wl_.events.size()))
            .end();
    }
    for (size_t i = 0; i < wl_.events.size(); ++i) push(wl_.events[i].obs.timestamp_ms, OBS_ARRIVAL, static_cast<int64_t>(i));
    if (always_on_) {
        // M7 detects continuously; it is woken once at t = 0 and never sleeps.
        m7_wake(0.0, -1);
        push(0.0, AO_CYCLE, 0);
    }
    while (!q_.empty()) {
        Ev e = q_.top();
        if (e.t >= T_) break;  // nothing happens at or after SIM_END
        q_.pop();
        switch (e.type) {
            case OBS_ARRIVAL: on_obs_arrival(e.t, e.a); break;
            case M4_WATCH_DONE: on_watch_done(e.t, e.a); break;
            case M4_SEC_DONE: on_sec_done(e.t, e.a); break;
            case M4_TX_DONE: on_tx_done(e.t, e.a); break;
            case M7_WAKE_DONE:
                wake_done_ms_ = e.t;
                if (log_.enabled(LOG_FULL)) log_.begin(e.t, "WAKE_DONE").end();
                m7_dequeue_and_start(e.t);
                break;
            case M7_STAGE1_DONE: on_stage1_done(e.t); break;
            case M7_STAGE2_DONE: on_stage2_done(e.t); break;
            case M7_POST_DONE: on_post_done(e.t); break;
            case RESULT_ARRIVE_M4: on_result_arrive(e.t, e.a); break;
            case M7_LINGER_END:
                if (static_cast<uint64_t>(e.a) == linger_gen_ && !m7_busy_ && m7_queue_.empty()) m7_sleep(e.t, false);
                break;
            case AO_CYCLE: on_ao_cycle(e.t); break;
        }
    }
    // SIM_END: close every open interval at T.
    if (m7_.state() != M7_SLEEP) m7_sleep(T_, true);
    m4_.finalize(T_);
    m7_.finalize(T_);
    for (const auto& w : wake_intervals_) sum_.m7_active_ms += w.second - w.first;
    sum_.observations = wl_.events.size();
    if (log_.enabled(LOG_DECISIONS)) {
        log_.begin(T_, "SIM_END").kvf("energy_mJ", energy_mj(), 3).kvf("m7_active_ms", sum_.m7_active_ms, 3).end();
    }
    log_.close();
}

// ---------------------------------------------------------------- M4 side

void Simulator::on_obs_arrival(double t, int64_t idx) {
    if (log_.enabled(LOG_FULL)) {
        const Observable& o = wl_.events[static_cast<size_t>(idx)].obs;
        log_begin_event(t, "OBSERVATION", idx);
        log_.kvf("duration_ms", o.duration_ms, 3).end();
    }
    if (always_on_) return;  // the M4 watcher is not used in always_on mode
    m4_queue_.push_back(idx);
    if (!m4_busy_) m4_start_next(t);
}

void Simulator::m4_start_next(double t) {
    if (m4_queue_.empty()) {
        m4_busy_ = false;
        m4_.set(t, M4_MONITOR);
        return;
    }
    const int64_t idx = m4_queue_.front();
    m4_queue_.pop_front();
    m4_busy_ = true;
    m4_.set(t, M4_PROCESS);
    rec_[static_cast<size_t>(idx)].m4_start_ms = t;
    push(t + cfg_.m4_process_ms, M4_WATCH_DONE, idx);
}

void Simulator::on_watch_done(double t, int64_t idx) {
    const Observable& o = wl_.events[static_cast<size_t>(idx)].obs;
    ObsRecord& r = rec_[static_cast<size_t>(idx)];
    WatcherFeatures f{o.motion_score, o.visual_score, o.temporal_change_score, o.sensor_consistency_score,
                      o.noise_score};
    WatcherDecision d = watcher_.evaluate(o.timestamp_ms, f);
    r.m4_evaluated = true;
    r.decision_ms = t;
    r.score = d.score;
    r.threshold = d.threshold;
    r.raw_positive = d.raw_positive;
    r.triggered = d.trigger;
    r.suppress_reason = d.suppress == WS_COOLDOWN ? "COOLDOWN" : (d.suppress == WS_BELOW_THRESHOLD ? "BELOW_THRESHOLD" : "NONE");
    ++sum_.watcher_evaluations;
    if (d.raw_positive) ++sum_.raw_positives;
    if (log_.enabled(LOG_FULL)) {
        log_begin_event(t, "WATCHER_SCORE", idx);
        log_.kvf("motion_score", o.motion_score)
            .kvf("visual_score", o.visual_score)
            .kvf("temporal_change_score", o.temporal_change_score)
            .kvf("sensor_consistency_score", o.sensor_consistency_score)
            .kvf("noise_score", o.noise_score)
            .kvf("score", d.score)
            .kvf("threshold", d.threshold)
            .end();
    }
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "WATCHER_DECISION", idx);
        log_.kvf("timestamp_ms", o.timestamp_ms, 3)
            .kvf("score", d.score)
            .kvf("threshold", d.threshold)
            .kv("decision", d.trigger ? "TRIGGER" : (d.raw_positive ? "SUPPRESSED" : "NO_TRIGGER"))
            .kvb("gt_is_legitimate", wl_.events[static_cast<size_t>(idx)].gt.is_legitimate)
            .kv("gt_action", wl_.events[static_cast<size_t>(idx)].gt.ground_truth_action)
            .end();
    }
    if (cfg_.security && d.raw_positive) gate_.note_candidate(o.timestamp_ms);
    if (!d.trigger) {
        if (d.raw_positive) {
            ++sum_.suppressed_cooldown;
            if (log_.enabled(LOG_DECISIONS)) {
                log_begin_event(t, "TRIGGER_SUPPRESSED", idx);
                log_.kv("reason", "COOLDOWN").end();
            }
        }
        m4_finish(t, idx);
        return;
    }
    ++sum_.triggers;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "TRIGGER", idx);
        log_.kvf("score", d.score).end();
    }
    if (cfg_.security) {
        m4_.set(t, SECURITY_PROCESSING);
        push(t + cfg_.security_process_ms, M4_SEC_DONE, idx);
    } else {
        send_request(t, idx);
    }
}

void Simulator::on_sec_done(double t, int64_t idx) {
    ObsRecord& r = rec_[static_cast<size_t>(idx)];
    SecurityDecision d = gate_.decide(frame_of(idx));
    std::string reason = security_reason_name(d.reason);
    if (d.accept && cfg_.debug_random_block_prob > 0.0) {
        // DEBUG ONLY: legacy probability-based blocking, kept for simulator
        // validation. Runs using it are flagged research_valid=false.
        Rng rb = Rng::keyed(cfg_.seed, "debug_block", wl_.events[static_cast<size_t>(idx)].obs.event_id);
        if (rb.bernoulli(cfg_.debug_random_block_prob)) {
            d.accept = false;
            reason = "DEBUG_RANDOM";
        }
    }
    r.sec_evaluated = true;
    r.sec_accept = d.accept;
    r.sec_reason = reason;
    r.sec_done_ms = t;
    r.consistency_metric = d.consistency_metric;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, d.accept ? "SECURITY_ACCEPT" : "SECURITY_BLOCK", idx);
        log_.kv("reason", reason)
            .kvf("consistency_metric", d.consistency_metric)
            .kv("burst_count", d.burst_count)
            .kv("rate_count", d.rate_count)
            .kvf("matched_age_ms", d.matched_age_ms, 3)
            .end();
    }
    if (!d.accept) {
        ++sum_.security_block;
        m4_finish(t, idx);  // a blocked trigger never reaches the M7
        return;
    }
    ++sum_.security_accept;
    send_request(t, idx);
}

void Simulator::send_request(double t, int64_t idx) {
    ObsRecord& r = rec_[static_cast<size_t>(idx)];
    const uint64_t id = wl_.events[static_cast<size_t>(idx)].obs.event_id;
    RpcTransfer x = rpc_.send(t, id, true);
    m4_.set(t, RPC_COMMUNICATION);
    r.rpc_send_ms = t;
    r.rpc_channel_wait_ms = x.channel_wait_ms;
    r.rpc_tx_ms = x.transmission_ms;
    r.rpc_status = x.lost ? "lost" : "in_flight";
    ++sum_.rpc_sent;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RPC_SEND", idx);
        log_.kv("dir", "M4_TO_M7").kvf("channel_wait_ms", x.channel_wait_ms, 3).kvf("tx_ms", x.transmission_ms, 3).end();
    }
    push(x.end_ms, M4_TX_DONE, idx);
}

void Simulator::on_tx_done(double t, int64_t idx) {
    ObsRecord& r = rec_[static_cast<size_t>(idx)];
    m4_finish(t, idx);
    if (r.rpc_status == "lost") {
        ++sum_.rpc_lost;
        if (log_.enabled(LOG_DECISIONS)) {
            log_begin_event(t, "RPC_DROP", idx);
            log_.kv("reason", "LOSS").end();
        }
        return;
    }
    r.rpc_receive_ms = t;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RPC_RECEIVE", idx);
        log_.kvf("total_rpc_ms", r.rpc_channel_wait_ms + r.rpc_tx_ms, 3).end();
    }
    if (static_cast<int>(m7_queue_.size()) >= cfg_.rpc_queue_capacity) {
        r.rpc_status = "queue_full";
        ++sum_.rpc_queue_full;
        if (log_.enabled(LOG_DECISIONS)) {
            log_begin_event(t, "RPC_DROP", idx);
            log_.kv("reason", "QUEUE_FULL").kv("queue_len", static_cast<int64_t>(m7_queue_.size())).end();
        }
        return;
    }
    r.rpc_status = "delivered";
    r.enqueue_ms = t;
    m7_queue_.push_back(Pending{idx, t});
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RPC_ENQUEUE", idx);
        log_.kv("queue_len", static_cast<int64_t>(m7_queue_.size())).end();
    }
    if (m7_.state() == M7_SLEEP) {
        r.caused_wake = true;
        m7_wake(t, idx);
    } else if (!m7_busy_) {
        // Lingering awake and idle: cancel the pending sleep and serve now.
        ++linger_gen_;
        m7_dequeue_and_start(t);
    }
}

void Simulator::m4_finish(double t, int64_t idx) {
    if (cfg_.security) gate_.observe(frame_of(idx));
    m4_start_next(t);
}

// ---------------------------------------------------------------- M7 side

void Simulator::m7_wake(double t, int64_t cause_idx) {
    ++sum_.wakes;
    wake_start_ms_ = t;
    m7_busy_ = true;
    if (log_.enabled(LOG_DECISIONS)) {
        log_.begin(t, "WAKE");
        if (cause_idx >= 0) log_.kv("event_id", wl_.events[static_cast<size_t>(cause_idx)].obs.event_id);
        else log_.kv("cause", "always_on");
        log_.end();
    }
    if (always_on_) {
        m7_.set(t, M7_IDLE_AWAKE);
        m7_busy_ = false;
        return;
    }
    m7_.set(t, M7_WAKEUP);
    push(t + cfg_.m7_wakeup_ms, M7_WAKE_DONE, 0);
}

void Simulator::m7_sleep(double t, bool forced) {
    ++sum_.sleeps;
    m7_.set(t, M7_SLEEP);
    m7_busy_ = false;
    wake_intervals_.push_back({wake_start_ms_, t});
    wake_forced_.push_back(forced);
    if (log_.enabled(LOG_DECISIONS)) {
        log_.begin(t, "SLEEP").kvb("forced_at_sim_end", forced).kvf("active_ms", t - wake_start_ms_, 3).end();
    }
}

void Simulator::m7_dequeue_and_start(double t) {
    if (m7_queue_.empty()) {
        m7_after_job(t);
        return;
    }
    Pending p = m7_queue_.front();
    m7_queue_.pop_front();
    ObsRecord& r = rec_[static_cast<size_t>(p.idx)];
    r.dequeue_ms = t;
    // A request that arrived while the M7 was waking waits for the wake-up
    // first; that part is reported separately from queueing behind jobs.
    const double ready = p.enq_ms > wake_done_ms_ ? p.enq_ms : wake_done_ms_;
    r.wake_wait_ms = ready - p.enq_ms;
    r.queue_delay_ms = t - ready;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RPC_DEQUEUE", p.idx);
        log_.kvf("queue_delay_ms", r.queue_delay_ms, 3).kvf("wake_wait_ms", r.wake_wait_ms, 3).end();
    }
    const WorkloadEvent& we = wl_.events[static_cast<size_t>(p.idx)];
    Job job;
    job.idx = p.idx;
    job.in.key = we.obs.event_id;
    job.in.background = false;
    job.in.frame_has_object = we.gt.frame_has_object;
    job.in.frame_class = we.gt.frame_object_class;
    job.in.visual_score = we.obs.visual_score;
    job.in.noise_score = we.obs.noise_score;
    start_job(t, job);
}

void Simulator::start_job(double t, const Job& job) {
    job_ = job;
    m7_busy_ = true;
    m7_.set(t, M7_INFERENCE);
    job_.s1 = det_->stage1(job_.in);
    if (job_.idx >= 0) {
        ObsRecord& r = rec_[static_cast<size_t>(job_.idx)];
        r.started = true;
        r.detect_start_ms = t;
        if (log_.enabled(LOG_DECISIONS)) {
            log_begin_event(t, "DETECT_START", job_.idx);
            log_.end();
        }
    }
    push(t + job_.s1.latency_ms, M7_STAGE1_DONE, 0);
}

void Simulator::on_stage1_done(double t) {
    const double c = job_.s1.confidence;
    if (job_.idx >= 0 && log_.enabled(LOG_FULL)) {
        log_begin_event(t, "STAGE1_DONE", job_.idx);
        log_.kvf("confidence", c).kv("predicted_class", class_name(job_.s1.predicted_class)).end();
    }
    const bool exit_now = cfg_.early_exit && (c >= cfg_.early_exit_threshold || c <= cfg_.early_exit_low_threshold);
    if (!exit_now) {
        job_.s2 = det_->stage2(job_.in, job_.s1);
        if (job_.s2.available) {
            job_.did_s2 = true;
            m7_.set(t, M7_SECOND_PASS);
            if (job_.idx >= 0 && log_.enabled(LOG_DECISIONS)) {
                log_begin_event(t, "SECOND_PASS", job_.idx);
                log_.kvf("stage1_confidence", c).end();
            }
            push(t + job_.s2.latency_ms, M7_STAGE2_DONE, 0);
            return;
        }
    } else if (job_.idx >= 0 && log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "EARLY_EXIT", job_.idx);
        log_.kvf("confidence", c).end();
    }
    job_.final_out = job_.s1;
    start_post(t);
}

void Simulator::on_stage2_done(double t) {
    job_.final_out = job_.s2;
    start_post(t);
}

void Simulator::start_post(double t) {
    m7_.set(t, M7_POSTPROCESS);
    const double post = det_->postprocess_ms(job_.in, job_.final_out);
    if (job_.idx >= 0) rec_[static_cast<size_t>(job_.idx)].post_ms = post;
    push(t + post, M7_POST_DONE, 0);
}

void Simulator::on_post_done(double t) {
    const bool detected = job_.final_out.confidence >= cfg_.detection_threshold;
    if (job_.did_s2) ++sum_.second_passes;
    else ++sum_.early_exits;
    if (job_.idx < 0) {
        ++sum_.bg_cycles;
        if (detected) ++sum_.bg_detections;
        m7_after_job(t);
        return;
    }
    ++sum_.results;
    ObsRecord& r = rec_[static_cast<size_t>(job_.idx)];
    r.processed = true;
    r.s1_conf = job_.s1.confidence;
    r.s1_class = job_.s1.predicted_class;
    r.s1_ms = job_.s1.latency_ms;
    r.second_pass = job_.did_s2;
    r.early_exit = !job_.did_s2;
    if (job_.did_s2) {
        r.s2_conf = job_.s2.confidence;
        r.s2_class = job_.s2.predicted_class;
        r.s2_ms = job_.s2.latency_ms;
    }
    r.final_conf = job_.final_out.confidence;
    r.final_class = detected ? job_.final_out.predicted_class : CLS_NONE;
    r.num_boxes = detected ? job_.final_out.num_boxes : 0;
    r.detected = detected;
    r.result_m7_ms = t;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RESULT", job_.idx);
        log_.kvb("detected", detected)
            .kv("predicted_class", class_name(r.final_class))
            .kvf("confidence", r.final_conf)
            .kvb("second_pass", r.second_pass)
            .end();
    }
    if (always_on_) {
        // Results stay on the M7; no inter-core message is needed.
        r.result_delivered_ms = t;
        ++sum_.results_delivered;
    } else {
        RpcTransfer x = rpc_.send(t, wl_.events[static_cast<size_t>(job_.idx)].obs.event_id, false);
        r.result_rpc_ms = x.channel_wait_ms + x.transmission_ms;
        push(x.end_ms, RESULT_ARRIVE_M4, job_.idx);
    }
    m7_after_job(t);
}

void Simulator::m7_after_job(double t) {
    job_ = Job();
    if (always_on_) {
        m7_busy_ = false;
        m7_.set(t, M7_IDLE_AWAKE);
        push(t, AO_CYCLE, 0);
        return;
    }
    if (!m7_queue_.empty()) {
        m7_dequeue_and_start(t);
        return;
    }
    m7_busy_ = false;
    if (cfg_.m7_linger_ms > 0.0) {
        m7_.set(t, M7_IDLE_AWAKE);
        ++linger_gen_;
        push(t + cfg_.m7_linger_ms, M7_LINGER_END, static_cast<int64_t>(linger_gen_));
    } else {
        m7_sleep(t, false);
    }
}

void Simulator::on_result_arrive(double t, int64_t idx) {
    ObsRecord& r = rec_[static_cast<size_t>(idx)];
    r.result_delivered_ms = t;
    ++sum_.results_delivered;
    if (log_.enabled(LOG_DECISIONS)) {
        log_begin_event(t, "RESULT_DELIVERED", idx);
        log_.kvf("trigger_to_result_ms", t - r.decision_ms, 3).end();
    }
}

void Simulator::on_ao_cycle(double t) {
    if (m7_busy_) return;
    // Admit every observation whose onset has passed.
    while (ao_next_ < wl_.events.size() && wl_.events[ao_next_].obs.timestamp_ms <= t) {
        ao_pending_.push_back(static_cast<int64_t>(ao_next_));
        ++ao_next_;
    }
    // Drop observations that are no longer visible.
    while (!ao_pending_.empty()) {
        const Observable& o = wl_.events[static_cast<size_t>(ao_pending_.front())].obs;
        if (o.timestamp_ms + o.duration_ms > t) break;
        ++sum_.ao_missed_observations;
        ao_pending_.pop_front();
    }
    Job job;
    if (!ao_pending_.empty()) {
        // Capture the earliest still-visible observation.
        size_t pick = 0;
        for (; pick < ao_pending_.size(); ++pick) {
            const Observable& o = wl_.events[static_cast<size_t>(ao_pending_[pick])].obs;
            if (o.timestamp_ms + o.duration_ms > t) break;
        }
        if (pick < ao_pending_.size()) {
            const int64_t idx = ao_pending_[pick];
            ao_pending_.erase(ao_pending_.begin() + static_cast<long>(pick));
            const WorkloadEvent& we = wl_.events[static_cast<size_t>(idx)];
            job.idx = idx;
            job.in.key = we.obs.event_id;
            job.in.frame_has_object = we.gt.frame_has_object;
            job.in.frame_class = we.gt.frame_object_class;
            job.in.visual_score = we.obs.visual_score;
            job.in.noise_score = we.obs.noise_score;
            start_job(t, job);
            return;
        }
    }
    // Background frame: empty scene at the scenario's noise level.
    job.idx = -1;
    job.bg_id = ++bg_counter_;
    job.in.key = job.bg_id;
    job.in.background = true;
    job.in.frame_has_object = false;
    job.in.visual_score = 0.1;
    // Empty-scene frames carry the scenario's background noise level.
    job.in.noise_score = bg_noise_;
    start_job(t, job);
}

// ---------------------------------------------------------------- outputs

double Simulator::state_time_ms(int core, int state) const {
    return core == 4 ? m4_.time_in(state) : m7_.time_in(state);
}

double Simulator::energy_mj() const {
    double e = 0.0;
    for (int s = 0; s < NUM_POWER_STATES; ++s) {
        const double t = is_m4_state(s) ? m4_.time_in(s) : m7_.time_in(s);
        e += pm_.power_mw[s] * t / 1000.0;
    }
    return e;
}

namespace {
const char* b(bool v) { return v ? "1" : "0"; }
}  // namespace

void Simulator::write_outputs(const std::string& dir, const std::string& workload_hash) const {
    {
        std::FILE* f = std::fopen((dir + "/observations.csv").c_str(), "wb");
        if (!f) throw std::runtime_error("cannot write observations.csv in " + dir);
        std::fprintf(f,
                     "event_id,episode_id,episode_type,timestamp_ms,duration_ms,is_legitimate,object_present,"
                     "object_class,attack_type,replay_id,burst_id,ground_truth_action,frame_has_object,"
                     "frame_object_class,m4_evaluated,decision_ms,score,threshold,raw_positive,triggered,"
                     "suppress_reason,sec_evaluated,sec_accept,sec_reason,consistency_metric,rpc_status,rpc_send_ms,"
                     "rpc_channel_wait_ms,rpc_tx_ms,rpc_receive_ms,enqueue_ms,dequeue_ms,queue_delay_ms,wake_wait_ms,caused_wake,"
                     "started,processed,detect_start_ms,s1_conf,s1_class,s1_ms,early_exit,second_pass,s2_conf,"
                     "s2_class,s2_ms,post_ms,final_conf,final_class,num_boxes,detected,result_m7_ms,"
                     "result_delivered_ms,result_rpc_ms\n");
        for (size_t i = 0; i < rec_.size(); ++i) {
            const Observable& o = wl_.events[i].obs;
            const GroundTruth& g = wl_.events[i].gt;
            const ObsRecord& r = rec_[i];
            std::fprintf(f,
                         "%llu,%lld,%s,%.3f,%.3f,%s,%s,%s,%s,%lld,%lld,%s,%s,%s,%s,%.3f,%.4f,%.4f,%s,%s,%s,%s,%s,%s,"
                         "%.4f,%s,%.3f,%.4f,%.4f,%.3f,%.3f,%.3f,%.3f,%.3f,%s,%s,%s,%.3f,%.4f,%s,%.3f,%s,%s,%.4f,%s,%.3f,"
                         "%.3f,%.4f,%s,%d,%s,%.3f,%.3f,%.4f\n",
                         static_cast<unsigned long long>(o.event_id), static_cast<long long>(g.episode_id),
                         g.episode_type.c_str(), o.timestamp_ms, o.duration_ms, b(g.is_legitimate), b(g.object_present),
                         class_name(g.object_class), g.attack_type.c_str(), static_cast<long long>(g.replay_id),
                         static_cast<long long>(g.burst_id), g.ground_truth_action.c_str(), b(g.frame_has_object),
                         class_name(g.frame_object_class), b(r.m4_evaluated), r.decision_ms, r.score, r.threshold,
                         b(r.raw_positive), b(r.triggered), r.suppress_reason.c_str(), b(r.sec_evaluated),
                         b(r.sec_accept), r.sec_reason.c_str(), r.consistency_metric, r.rpc_status.c_str(),
                         r.rpc_send_ms, r.rpc_channel_wait_ms, r.rpc_tx_ms, r.rpc_receive_ms, r.enqueue_ms,
                         r.dequeue_ms, r.queue_delay_ms, r.wake_wait_ms, b(r.caused_wake), b(r.started), b(r.processed),
                         r.detect_start_ms, r.s1_conf, class_name(r.s1_class), r.s1_ms, b(r.early_exit),
                         b(r.second_pass), r.s2_conf, class_name(r.s2_class), r.s2_ms, r.post_ms, r.final_conf,
                         class_name(r.final_class), r.num_boxes, b(r.detected), r.result_m7_ms, r.result_delivered_ms,
                         r.result_rpc_ms);
        }
        std::fclose(f);
    }
    {
        std::FILE* f = std::fopen((dir + "/states.csv").c_str(), "wb");
        std::fprintf(f, "core,state,time_ms,power_mW,energy_mJ\n");
        for (int s = 0; s < NUM_POWER_STATES; ++s) {
            const bool m4 = is_m4_state(s);
            const double t = m4 ? m4_.time_in(s) : m7_.time_in(s);
            std::fprintf(f, "%s,%s,%.3f,%.4f,%.6f\n", m4 ? "M4" : "M7", power_state_name(s), t, pm_.power_mw[s],
                         pm_.power_mw[s] * t / 1000.0);
        }
        std::fclose(f);
    }
    {
        std::FILE* f = std::fopen((dir + "/wake_intervals.csv").c_str(), "wb");
        std::fprintf(f, "wake_ms,sleep_ms,active_ms,forced_at_sim_end\n");
        for (size_t i = 0; i < wake_intervals_.size(); ++i)
            std::fprintf(f, "%.3f,%.3f,%.3f,%s\n", wake_intervals_[i].first, wake_intervals_[i].second,
                         wake_intervals_[i].second - wake_intervals_[i].first, b(wake_forced_[i]));
        std::fclose(f);
    }
    {
        std::FILE* f = std::fopen((dir + "/summary.json").c_str(), "wb");
        const RunSummary& s = sum_;
        const bool research_valid = cfg_.debug_random_block_prob <= 0.0;
        std::fprintf(f,
                     "{\n  \"simulator_version\": \"edge_sim-1.0\",\n  \"mode\": \"%s\",\n  \"scenario\": \"%s\",\n"
                     "  \"seed\": %llu,\n  \"seconds\": %.3f,\n  \"workload_hash_fnv1a64\": \"%s\",\n"
                     "  \"detector_backend\": \"%s\",\n  \"power_model_source\": \"%s\",\n"
                     "  \"power_model_calibrated\": %s,\n  \"research_valid\": %s,\n"
                     "  \"observations\": %llu,\n  \"watcher_evaluations\": %llu,\n  \"raw_positives\": %llu,\n"
                     "  \"triggers\": %llu,\n  \"suppressed_cooldown\": %llu,\n  \"security_accept\": %llu,\n"
                     "  \"security_block\": %llu,\n  \"rpc_sent\": %llu,\n  \"rpc_lost\": %llu,\n"
                     "  \"rpc_queue_full\": %llu,\n  \"wakes\": %llu,\n  \"sleeps\": %llu,\n  \"results\": %llu,\n"
                     "  \"results_delivered\": %llu,\n  \"early_exits\": %llu,\n  \"second_passes\": %llu,\n"
                     "  \"bg_cycles\": %llu,\n  \"bg_detections\": %llu,\n  \"ao_missed_observations\": %llu,\n"
                     "  \"m7_active_ms\": %.3f,\n  \"duty_cycle\": %.6f,\n  \"energy_mJ\": %.6f,\n"
                     "  \"event_log_lines\": %llu\n}\n",
                     cfg_.mode.c_str(), wl_.scenario.c_str(), static_cast<unsigned long long>(cfg_.seed), cfg_.seconds,
                     workload_hash.c_str(), det_->name().c_str(), pm_.source.c_str(), pm_.calibrated ? "true" : "false",
                     research_valid ? "true" : "false", static_cast<unsigned long long>(s.observations),
                     static_cast<unsigned long long>(s.watcher_evaluations),
                     static_cast<unsigned long long>(s.raw_positives), static_cast<unsigned long long>(s.triggers),
                     static_cast<unsigned long long>(s.suppressed_cooldown),
                     static_cast<unsigned long long>(s.security_accept),
                     static_cast<unsigned long long>(s.security_block), static_cast<unsigned long long>(s.rpc_sent),
                     static_cast<unsigned long long>(s.rpc_lost), static_cast<unsigned long long>(s.rpc_queue_full),
                     static_cast<unsigned long long>(s.wakes), static_cast<unsigned long long>(s.sleeps),
                     static_cast<unsigned long long>(s.results), static_cast<unsigned long long>(s.results_delivered),
                     static_cast<unsigned long long>(s.early_exits), static_cast<unsigned long long>(s.second_passes),
                     static_cast<unsigned long long>(s.bg_cycles), static_cast<unsigned long long>(s.bg_detections),
                     static_cast<unsigned long long>(s.ao_missed_observations), s.m7_active_ms,
                     T_ > 0 ? s.m7_active_ms / T_ : 0.0, energy_mj(), static_cast<unsigned long long>(log_.lines()));
        std::fclose(f);
    }
}

}  // namespace sim
