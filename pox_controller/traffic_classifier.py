"""
Traffic Classification System - POX Controller
Classifies TCP, UDP, ICMP packets and maintains statistics
"""

from pox.core import core
from pox.lib.revent import EventMixin
import pox.openflow.libopenflow_01 as of
from pox.lib.packet import ethernet, ipv4, tcp, udp, icmp
from pox.lib.addresses import IPAddr
from collections import defaultdict
import time, threading

log = core.getLogger()

class TrafficClassifier(EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)

        # MAC learning: {dpid: {mac: port}}
        self.mac_to_port = {}

        # Protocol stats: {dpid: {proto: count}}
        self.stats = defaultdict(lambda: defaultdict(int))

        # Per-host stats: {dpid: {src_ip: {proto: count}}}
        self.host_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        # Start background stats printer every 15 seconds
        t = threading.Thread(target=self._monitor, daemon=True)
        t.start()

        log.info("Traffic Classifier started!")

    # ----------------------------
    # Switch connects
    # ----------------------------
    def _handle_ConnectionUp(self, event):
        log.info("Switch %s connected", event.dpid)
        # Install table-miss: send all unmatched packets to controller
        msg = of.ofp_flow_mod()
        msg.priority = 0
        msg.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        event.connection.send(msg)

    # ----------------------------
    # Packet-In: core logic
    # ----------------------------
    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        dpid    = event.dpid
        in_port = event.port
        connection = event.connection

        # --- MAC LEARNING ---
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][packet.src] = in_port

        # Decide output port
        if packet.dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][packet.dst]
        else:
            out_port = of.OFPP_FLOOD

        # --- TRAFFIC CLASSIFICATION ---
        ip_pkt = packet.find('ipv4')
        if ip_pkt:
            src_ip = str(ip_pkt.srcip)
            dst_ip = str(ip_pkt.dstip)
            proto_label = "OTHER"

            tcp_pkt  = packet.find('tcp')
            udp_pkt  = packet.find('udp')
            icmp_pkt = packet.find('icmp')

            if tcp_pkt:
                proto_label = "TCP"
                if out_port != of.OFPP_FLOOD:
                    self._install_flow(connection, in_port, out_port,
                                       ip_pkt.srcip, ip_pkt.dstip, 6)

            elif udp_pkt:
                proto_label = "UDP"
                if out_port != of.OFPP_FLOOD:
                    self._install_flow(connection, in_port, out_port,
                                       ip_pkt.srcip, ip_pkt.dstip, 17)

            elif icmp_pkt:
                proto_label = "ICMP"
                if out_port != of.OFPP_FLOOD:
                    self._install_flow(connection, in_port, out_port,
                                       ip_pkt.srcip, ip_pkt.dstip, 1)

            # Update stats
            self.stats[dpid][proto_label] += 1
            self.host_stats[dpid][src_ip][proto_label] += 1

            log.info("[CLASSIFY] Switch:%s  %s -> %s  [%s]",
                     dpid, src_ip, dst_ip, proto_label)

        # Send packet out
        msg = of.ofp_packet_out()
        msg.in_port = in_port
        msg.data = event.ofp
        msg.actions.append(of.ofp_action_output(port=out_port))
        connection.send(msg)

    # ----------------------------
    # Install a flow rule
    # ----------------------------
    def _install_flow(self, connection, in_port, out_port,
                      src_ip, dst_ip, proto):
        msg = of.ofp_flow_mod()
        msg.priority = 10
        msg.idle_timeout = 10
        msg.match.in_port  = in_port
        msg.match.dl_type  = 0x0800   # IPv4
        msg.match.nw_proto = proto
        msg.match.nw_src   = src_ip
        msg.match.nw_dst   = dst_ip
        msg.actions.append(of.ofp_action_output(port=out_port))
        connection.send(msg)

    # ----------------------------
    # Background stats printer
    # ----------------------------
    def _monitor(self):
        while True:
            time.sleep(15)
            self._print_stats()

    def _print_stats(self):
        print("\n" + "="*55)
        print("      TRAFFIC CLASSIFICATION STATISTICS")
        print("="*55)
        if not self.stats:
            print("  No traffic seen yet.")
        for dpid, protocols in self.stats.items():
            total = sum(protocols.values())
            print(f"\n  Switch {dpid} | Total packets classified: {total}")
            for proto, count in sorted(protocols.items()):
                pct = (count / total * 100) if total else 0
                bar = "█" * int(pct / 5)
                print(f"   {proto:<6}: {count:>5} pkts  {pct:5.1f}%  {bar}")
        print("\n  Per-Host Breakdown:")
        for dpid, hosts in self.host_stats.items():
            for ip, protos in sorted(hosts.items()):
                parts = "  ".join(f"{p}:{c}" for p, c in sorted(protos.items()))
                print(f"   {ip:<15} -> {parts}")
        print("="*55 + "\n")


def launch():
    core.registerNew(TrafficClassifier)
