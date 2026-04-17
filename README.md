# Traffic Classification System — SDN Mininet Project
### COMPUTER NETWORKS - UE24CS252B | PES University
#### Sneha Angelin Jisho - PES2UG24CS507 (Section - I)

---

## Problem Statement

Implement an SDN-based Traffic Classification System using Mininet and the POX OpenFlow controller that:
- Identifies and classifies network packets by protocol type: **TCP, UDP, and ICMP**
- Maintains per-protocol and per-host traffic statistics
- Displays real-time classification results via controller logs
- Analyzes traffic distribution across protocols
- Installs explicit OpenFlow flow rules per classified flow

---

## Tools & Technologies

| Tool | Purpose |
|------|---------|
| Mininet | Network emulation (virtual hosts + switch) |
| POX Controller | OpenFlow SDN controller (Python 3) |
| Open vSwitch (OVS) | Software switch managed via OpenFlow |
| iperf | TCP and UDP traffic generation |
| ovs-ofctl | Flow table inspection |

---

## Topology

```
h1 (10.0.0.1) ─┐
h2 (10.0.0.2) ──── s1 (OpenFlow Switch) ──── POX Controller
h3 (10.0.0.3) ─┘
```

3 hosts connected to 1 OpenFlow switch, controlled by POX running on localhost:6633.

---

## Project Structure

```
traffic_classifier/
├── topology.py              # Mininet topology (3 hosts, 1 switch)
~/pox/pox/ext/
└── traffic_classifier.py    # POX controller — classification logic
```

---

## Setup & Installation

### Prerequisites
- Ubuntu Linux (20.04 / 22.04 / 25.04)
- Python 3
- Mininet
- POX Controller
- iperf

### Step 1 — Install Mininet
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install mininet iperf -y
```

### Step 2 — Clone POX Controller
```bash
cd ~
git clone https://github.com/noxrepo/pox.git
```

### Step 3 — Install the Controller
```bash
# Create ext directory if it doesn't exist
mkdir -p ~/pox/pox/ext
touch ~/pox/pox/ext/__init__.py

# Copy controller into POX's ext folder
cp traffic_classifier.py ~/pox/pox/ext/
```

### Step 4 — Clone This Repo
```bash
git clone https://github.com/YOURUSERNAME/traffic-classifier.git
cd traffic-classifier
```

---

## Running the Project

> You need **two terminals** open simultaneously.

### Terminal 1 — Start POX Controller
```bash
cd ~/pox
python3 pox.py log.level --DEBUG ext.traffic_classifier
```

Wait for:
```
INFO:traffic_classifier:Traffic Classifier started!
INFO:core:POX 0.7.0 (gar) is up.
DEBUG:openflow.of_01:Listening on 0.0.0.0:6633
```

### Terminal 2 — Start Mininet Topology
```bash
sudo mn -c   # clean up any previous state
sudo python3 topology.py
```

Wait for `mininet>` prompt.

---

## How It Works

### Controller Logic

1. **Table-miss rule** installed on switch connect — all unmatched packets sent to controller
2. **`packet_in` handler** inspects every packet:
   - Extracts IPv4 header
   - Checks for TCP (`nw_proto=6`), UDP (`nw_proto=17`), ICMP (`nw_proto=1`)
   - Logs classification: `[CLASSIFY] Switch:1  10.0.0.1 -> 10.0.0.2  [ICMP]`
   - Updates statistics counters
3. **Flow rule installed** per classified flow (priority=10, idle_timeout=10s) — subsequent packets bypass controller
4. **Background thread** prints full statistics table every 15 seconds

### Match-Action Flow Rule Design

| Protocol | nw_proto | Priority | Action |
|----------|----------|----------|--------|
| ICMP | 1 | 10 | Forward to learned port |
| TCP | 6 | 10 | Forward to learned port |
| UDP | 17 | 10 | Forward to learned port |
| Default (miss) | any | 0 | Send to Controller |

---

## Test Scenarios & Results

### Scenario 1 — ICMP Traffic (Normal connectivity test)

```
mininet> h1 ping -c 5 h2
```

**Expected:** 5 packets transmitted, 0% packet loss. Controller classifies as ICMP.

### Scenario 2 — TCP Traffic (iperf throughput test)

```
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 5
```

**Expected:** High throughput TCP session. Controller classifies as TCP and installs flow rule.

### Scenario 3 — UDP Traffic (iperf UDP test)

```
mininet> h3 iperf -s -u &
mininet> h1 iperf -c 10.0.0.3 -u -t 5
```

**Expected:** UDP datagrams sent, 0% loss. Controller classifies as UDP.

### Check Flow Tables (while traffic is running)

```
mininet> sh ovs-ofctl dump-flows s1
```

---

## Expected Output

### Controller Classification Logs
```
INFO:traffic_classifier:[CLASSIFY] Switch:1  10.0.0.1 -> 10.0.0.2  [ICMP]
INFO:traffic_classifier:[CLASSIFY] Switch:1  10.0.0.2 -> 10.0.0.1  [ICMP]
INFO:traffic_classifier:[CLASSIFY] Switch:1  10.0.0.1 -> 10.0.0.2  [TCP]
INFO:traffic_classifier:[CLASSIFY] Switch:1  10.0.0.1 -> 10.0.0.3  [UDP]
```

### Statistics Table (printed every 15 seconds)
```
=======================================================
      TRAFFIC CLASSIFICATION STATISTICS
=======================================================
  Switch 1 | Total packets classified: 6
   ICMP  :     2 pkts   33.3%
   TCP   :     2 pkts   33.3%
   UDP   :     2 pkts   33.3%

  Per-Host Breakdown:
   10.0.0.1        -> ICMP:1  TCP:1  UDP:1
   10.0.0.2        -> ICMP:1  TCP:1
   10.0.0.3        -> UDP:1
=======================================================
```

---

## Proof of Execution

### Screenshot 1 — Both Terminals: Controller + Topology Running

> POX showing "Switch 1 connected" alongside Mininet showing the `mininet>` prompt with h1, h2, h3 connected.

![Screenshot 1 - Setup](screenshots/screenshot1_setup.png)

---

### Screenshot 2 — ICMP Test: Ping Results + Classification

> Left: POX terminal showing ICMP classification stats (100% ICMP, per-host breakdown).
> Right: Mininet terminal showing `h1 ping -c 5 h2` — 5 packets, 0% packet loss.

![Screenshot 2 - ICMP](screenshots/screenshot2_icmp.png)

---

### Screenshot 3 — TCP Test: iperf Results + Updated Stats

> Left: POX stats updated to ICMP 50% / TCP 50%.
> Right: Mininet terminal showing TCP iperf — 108 Gbits/sec throughput.

![Screenshot 3 - TCP](screenshots/screenshot3_tcp.png)

---

### Screenshot 4 — UDP Test: iperf Results + All 3 Protocols Classified

> Left: POX [CLASSIFY] lines showing UDP detection + stats table showing ICMP/TCP/UDP all at 33.3%.
> Right: Mininet terminal showing UDP iperf — 1.05 Mbits/sec, 0% loss, 448 datagrams.

![Screenshot 4 - UDP](screenshots/screenshot4_udp.png)

---

### Screenshot 5 — Final Statistics Table: All 3 Protocols

> POX terminal showing complete traffic distribution:
> - ICMP: 2 pkts 33.3%
> - TCP: 2 pkts 33.3%
> - UDP: 2 pkts 33.3%
> - Per-host breakdown: h1 sent all 3 types, h2 received ICMP+TCP, h3 received UDP

![Screenshot 5 - Stats](screenshots/screenshot5_stats.png)

---

### Screenshot 6 — Flow Table: ICMP Rules Active

> `ovs-ofctl dump-flows s1` showing:
> - Rule 1: `priority=10, icmp, nw_src=10.0.0.1, nw_dst=10.0.0.2` → forward
> - Rule 2: `priority=10, icmp, nw_src=10.0.0.2, nw_dst=10.0.0.1` → forward
> - Rule 3: `priority=0` → send to CONTROLLER

![Screenshot 6 - Flow Table ICMP](screenshots/screenshot6_flowtable_icmp.png)

---

### Screenshot 7 — Flow Table: ICMP + TCP Rules Active

> `ovs-ofctl dump-flows s1` during iperf showing:
> - ICMP rules (62 packets each direction)
> - TCP rules: `priority=10, tcp, nw_src=10.0.0.1` — 1.8M packets, 83GB transferred
> - Default table-miss rule

![Screenshot 7 - Flow Table TCP](screenshots/screenshot7_flowtable_tcp.png)

---

## References

1. Mininet Overview — https://mininet.org/overview/
2. Mininet Walkthrough — https://mininet.org/walkthrough/
3. POX Controller Wiki — https://noxrepo.github.io/pox-doc/html/
4. POX GitHub — https://github.com/noxrepo/pox
5. OpenFlow 1.0 Specification — https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf
6. Open vSwitch — https://www.openvswitch.org/
