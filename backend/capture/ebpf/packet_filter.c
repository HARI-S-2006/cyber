#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/icmp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_PACKET_SIZE 1500
#define PAYLOAD_CAPTURE_LEN 128
#define MAX_FLOWS 100000

struct flow_key {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
    __u8 pad[3];
};

struct packet_metadata {
    __u64 timestamp_ns;
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
    __u8 tcp_flags;
    __u16 payload_len;
    __u8 payload[PAYLOAD_CAPTURE_LEN];
    __u32 pkt_len;
    __u8 direction;
};

struct flow_stats {
    __u64 start_time_ns;
    __u64 last_time_ns;
    __u64 packets_fwd;
    __u64 packets_bwd;
    __u64 bytes_fwd;
    __u64 bytes_bwd;
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8 protocol;
    __u8 tcp_flags_seen;
    __u8 active;
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 24);
} packet_ringbuf SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, MAX_FLOWS);
    __type(key, struct flow_key);
    __type(value, struct flow_stats);
} flow_table SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} config_map SEC(".maps");

static __always_inline int parse_ipv4(void *data, void *data_end, struct packet_metadata *meta) {
    struct iphdr *ip = data;
    if ((void *)(ip + 1) > data_end)
        return -1;

    meta->src_ip = ip->saddr;
    meta->dst_ip = ip->daddr;
    meta->protocol = ip->protocol;
    meta->pkt_len = bpf_ntohs(ip->tot_len);

    void *transport = (void *)ip + (ip->ihl * 4);
    if (transport > data_end)
        return -1;

    switch (ip->protocol) {
        case IPPROTO_TCP: {
            struct tcphdr *tcp = transport;
            if ((void *)(tcp + 1) > data_end)
                return -1;
            meta->src_port = bpf_ntohs(tcp->source);
            meta->dst_port = bpf_ntohs(tcp->dest);
            meta->tcp_flags = tcp->fin | (tcp->syn << 1) | (tcp->rst << 2) | (tcp->psh << 3) | (tcp->ack << 4) | (tcp->urg << 5);
            
            __u16 payload_offset = ip->ihl * 4 + tcp->doff * 4;
            void *payload = (void *)ip + payload_offset;
            __u16 payload_len = meta->pkt_len - payload_offset;
            if (payload_len > PAYLOAD_CAPTURE_LEN)
                payload_len = PAYLOAD_CAPTURE_LEN;
            if (payload + payload_len <= data_end) {
                __builtin_memcpy(meta->payload, payload, payload_len);
                meta->payload_len = payload_len;
            }
            break;
        }
        case IPPROTO_UDP: {
            struct udphdr *udp = transport;
            if ((void *)(udp + 1) > data_end)
                return -1;
            meta->src_port = bpf_ntohs(udp->source);
            meta->dst_port = bpf_ntohs(udp->dest);
            
            __u16 payload_offset = ip->ihl * 4 + sizeof(struct udphdr);
            void *payload = (void *)ip + payload_offset;
            __u16 payload_len = bpf_ntohs(udp->len) - sizeof(struct udphdr);
            if (payload_len > PAYLOAD_CAPTURE_LEN)
                payload_len = PAYLOAD_CAPTURE_LEN;
            if (payload + payload_len <= data_end) {
                __builtin_memcpy(meta->payload, payload, payload_len);
                meta->payload_len = payload_len;
            }
            break;
        }
        case IPPROTO_ICMP: {
            struct icmphdr *icmp = transport;
            if ((void *)(icmp + 1) > data_end)
                return -1;
            meta->src_port = 0;
            meta->dst_port = 0;
            break;
        }
        default:
            return -1;
    }
    return 0;
}

SEC("xdp")
int xdp_packet_filter(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;

    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    struct packet_metadata *meta = bpf_ringbuf_reserve(&packet_ringbuf, sizeof(*meta), 0);
    if (!meta)
        return XDP_PASS;

    meta->timestamp_ns = bpf_ktime_get_ns();
    meta->direction = 0;

    if (parse_ipv4(data + sizeof(struct ethhdr), data_end, meta) < 0) {
        bpf_ringbuf_discard(meta, 0);
        return XDP_PASS;
    }

    struct flow_key fkey = {
        .src_ip = meta->src_ip,
        .dst_ip = meta->dst_ip,
        .src_port = meta->src_port,
        .dst_port = meta->dst_port,
        .protocol = meta->protocol,
    };

    struct flow_stats *stats = bpf_map_lookup_elem(&flow_table, &fkey);
    if (!stats) {
        struct flow_stats new_stats = {
            .start_time_ns = meta->timestamp_ns,
            .last_time_ns = meta->timestamp_ns,
            .packets_fwd = 1,
            .bytes_fwd = meta->pkt_len,
            .src_ip = meta->src_ip,
            .dst_ip = meta->dst_ip,
            .src_port = meta->src_port,
            .dst_port = meta->dst_port,
            .protocol = meta->protocol,
            .tcp_flags_seen = meta->tcp_flags,
            .active = 1,
        };
        bpf_map_update_elem(&flow_table, &fkey, &new_stats, BPF_ANY);
    } else {
        stats->last_time_ns = meta->timestamp_ns;
        stats->packets_fwd++;
        stats->bytes_fwd += meta->pkt_len;
        stats->tcp_flags_seen |= meta->tcp_flags;
    }

    bpf_ringbuf_submit(meta, 0);
    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";