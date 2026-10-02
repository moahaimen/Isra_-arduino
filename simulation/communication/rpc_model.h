// Inter-core RPC model (M4 <-> M7 mailbox / shared-memory messaging).
//
//   transmission_ms = rpc_latency_ms + rpc_jitter_ms * |N(0,1)|
//   channel_wait_ms = max(0, channel_free_at - t_request)   (contention)
//   total_rpc_ms    = channel_wait_ms + transmission_ms
//
// The channel carries one message at a time in both directions, so trigger
// requests and result messages contend for it. Losses are Bernoulli with
// probability rpc_loss on request messages; with rpc_loss == 0 no message is
// ever dropped for loss (queue overflow drops are modelled in the simulator).
// Queue delay at the M7 work queue is tracked by the simulator core.
#pragma once

#include <cmath>
#include <cstdint>

#include "config/sim_config.h"
#include "core/rng.h"

namespace sim {

struct RpcTransfer {
    double request_ms = 0.0;
    double start_ms = 0.0;
    double end_ms = 0.0;
    double channel_wait_ms = 0.0;
    double transmission_ms = 0.0;
    bool lost = false;
};

class RpcChannel {
public:
    explicit RpcChannel(const SimConfig& cfg) : cfg_(cfg) {}

    RpcTransfer send(double t_request, uint64_t key, bool m4_to_m7) {
        RpcTransfer x;
        x.request_ms = t_request;
        x.start_ms = t_request > free_at_ ? t_request : free_at_;
        x.channel_wait_ms = x.start_ms - t_request;
        Rng r = Rng::keyed(cfg_.seed, m4_to_m7 ? "rpc_tx_req" : "rpc_tx_res", key);
        x.transmission_ms = cfg_.rpc_latency_ms + cfg_.rpc_jitter_ms * std::fabs(r.normal(0.0, 1.0));
        x.end_ms = x.start_ms + x.transmission_ms;
        free_at_ = x.end_ms;
        if (m4_to_m7 && cfg_.rpc_loss > 0.0) {
            Rng lr = Rng::keyed(cfg_.seed, "rpc_loss", key);
            x.lost = lr.bernoulli(cfg_.rpc_loss);
        }
        ++messages_;
        return x;
    }

    uint64_t messages() const { return messages_; }

private:
    const SimConfig& cfg_;
    double free_at_ = 0.0;
    uint64_t messages_ = 0;
};

}  // namespace sim
