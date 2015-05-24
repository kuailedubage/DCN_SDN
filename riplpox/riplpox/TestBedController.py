"""
RipL+POX.  As simple a data center controller as possible.
"""

import logging
import random
from struct import pack
from zlib import crc32

from collections import defaultdict
import time

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import EventMixin
from pox.lib.addresses import EthAddr
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.udp import udp
from pox.lib.packet.tcp import tcp

from ripl.mn import topos

from util import buildTopo, getRouting

log = core.getLogger()

# Number of bytes to send for packet_ins
MISS_SEND_LEN = 2000

MODES = ['reactive', 'proactive']
DEF_MODE = MODES[0]

IDLE_TIMEOUT = 20
HARD_TIMEOUT = 60

# Borrowed from pox/forwarding/l2_multi


class Switch(object):
    def __init__(self):
        self.connection = None
        self.ports = None
        self.dpid = None
        self._listeners = None

    def __repr__(self):
        pass

    def disconnect(self):
        if self.connection is not None:
            log.debug("Disconnect %s" % (self.connection,))
            self.connection.removeListeners(self._listeners)
            self.connection = None
            self._listeners = None

    def connect(self, connection):
        if self.dpid is None:
            self.dpid = connection.dpid
        assert self.dpid == connection.dpid
        if self.ports is None:
            self.ports = connection.features.ports
        self.disconnect()
        log.debug("Connect %s" % (connection,))
        self.connection = connection
        self._listeners = connection.addListeners(self)

    def send_packet_data(self, outport, data=None):
        msg = of.ofp_packet_out(in_port=of.OFPP_NONE, data=data)
        msg.actions.append(of.ofp_action_output(port=outport))
        self.connection.send(msg)

    def install(self, port, match, buf=None, idle_timeout=0, hard_timeout=0,
                priority=of.OFP_DEFAULT_PRIORITY):
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        # msg.priority = priority
        msg.actions.append(of.ofp_action_output(port=port))
        msg.buffer_id = buf
        # print "install-------------------------", self.connection
        self.connection.send(msg)

    def install_multiple(self, actions, match, buf=None, idle_timeout=0,
                         hard_timeout=0, priority=of.OFP_DEFAULT_PRIORITY):
        msg = of.ofp_flow_mod()
        msg.match = match
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        msg.priority = priority
        for a in actions:
            msg.actions.append(a)
        msg.buffer_id = buf
        self.connection.send(msg)

    def _handle_ConnectionDown(self, event):
        self.disconnect()
        pass


class TestBedController(object):
    def __init__(self, t, r, mode):
        self.switches = {}  # Switches seen: [dpid] -> Switch
        self.t = t  # Master Topo object, passed in and never modified.
        self.r = r  # Master Routing object, passed in and reused.
        self.mode = mode  # One in MODES.
        self.macTable = {}  # [mac] -> (dpid, port)
        self.portsMap = {
            'sc1': {'sa3': (41, 33), 'sa4': (43, 29), 'sa7': (42, 17), 'sa8': (44, 13)},
            'sc2': {'sa3': (37, 35), 'sa4': (39, 31), 'sa7': (38, 19), 'sa8': (40, 15)},
            'sa3': {'sc1': (33, 41), 'sc2': (35, 37), 'se5': (34, 27), 'se6': (36, 21)},
            'sa4': {'sc1': (29, 43), 'sc2': (31, 39), 'se5': (30, 26), 'se6': (32, 23)},
            'se5': {'sa3': (27, 34), 'sa4': (26, 30)},
            'se6': {'sa3': (21, 36), 'sa4': (23, 32)},
            'sa7': {'sc1': (17, 42), 'sc2': (19, 38), 'se9': (18, 9), 'se10': (20, 7)},
            'sa8': {'sc1': (13, 44), 'sc2': (15, 40), 'se9': (16, 11), 'se10': (14, 6)},
            'se9': {'sa7': (9, 18), 'sa8': (11, 16)},
            'se10': {'sa7': (7, 20), 'sa8': (6, 14)}
            }

        # TODO: generalize all_switches_up to a more general state machine.
        self.all_switches_up = False  # Sequences event handling.
        core.openflow.addListeners(self, priority=0)

    def _ecmp_hash(self, packet):
        "Return an ECMP-style 5-tuple hash for TCP/IP packets, otherwise 0."
        hash_input = [0] * 5
        if isinstance(packet.next, ipv4):
            ip = packet.next
            hash_input[0] = ip.srcip.toUnsigned()
            hash_input[1] = ip.dstip.toUnsigned()
            hash_input[2] = ip.protocol
            if isinstance(ip.next, tcp) or isinstance(ip.next, udp):
                l4 = ip.next
                hash_input[3] = l4.srcport
                hash_input[4] = l4.dstport
                return crc32(pack('LLHHH', *hash_input))
        return 0

    def _install_reactive_path(self, event, out_sw_str, final_out_port, packet):
        "Install entries on route between two switches."
        in_name = self._connToStr(event.connection)
        out_name = out_sw_str
        hash_ = self._ecmp_hash(packet)
        # log.info(("%s-->%s" % sr)
        route = self.r.get_route(in_name, out_name, hash_)
        # log.info("route: %s" % route)
        # match = of.ofp_match.from_packet(packet)
        match = of.ofp_match()
        match.dl_src = packet.src
        match.dl_dst = packet.dst
        for i, node in enumerate(route):
            if i < len(route) - 1:
                next_node = route[i + 1]
                out_port, next_in_port = self._getports(node, next_node)
                # print node, out_port, next_node, next_in_port,
            else:
                # print final_out_port
                out_port = final_out_port
            self.switches[node].install(out_port, match, idle_timeout=IDLE_TIMEOUT, hard_timeout=HARD_TIMEOUT)

    def _getports(self, node1, node2):
        return self.portsMap[node1][node2]

    def _connToStr(self, conn_name):
        # [f0-92-1c-22-ca-c0|24 2]
        conn2name = {1: 'sc1', 2: 'sc2', 3: 'sa3', 4: 'sa4', 5: 'se5', 6: 'se6',
                     7: 'sa7', 8: 'sa8', 9: 'se9', 0: 'se10'}
        # print str(conn_name)
        return conn2name[int(str(conn_name)[20:21])]

    def _drop(self, event):
        # Kill the buffer
        if event.ofp.buffer_id is not None:
            msg = of.ofp_packet_out()
            msg.buffer_id = event.ofp.buffer_id
            event.ofp.buffer_id = None  # Mark is dead
            msg.in_port = event.port
            self.connection.send(msg)

    def _flood(self, event):
        packet = event.parsed
        dpid = event.dpid
        # log.info("PacketIn: %s" % packet)
        in_port = event.port
        t = self.t

        # Broadcast to every output port except the input on the input switch.
        # Hub behavior, baby!
        sw_name = self._connToStr(event.connection)

        flood_ports = defaultdict(lambda: [])
        edg_sw = {'se5': (25, 18), 'se6': (22, 24), 'se9': (10, 12), 'se10': (5, 8)}
        for sw in edg_sw:
            # msg = of.ofp_packet_out(data=event.ofp)
            # OFPP_FLOOD is optional; some switches may need OFPP_ALL
            # msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            # msg.buffer_id = event.ofp.buffer_id
            # msg.in_port = event.port
            for port in edg_sw[sw]:
                self.switches[sw].send_packet_data(port, event.data)

    def _handle_packet_reactive(self, event):
        packet = event.parsed
        # dpid = event.dpid
        # log.info("PacketIn: %s" % packet)
        in_port = event.port
        t = self.t

        # Learn MAC address of the sender on every packet-in.
        if packet.src not in self.macTable:
            sw_str = self._connToStr(event.connection)
            self.macTable[packet.src] = (sw_str, in_port)
        # print self.macTable
        # log.info("mactable: %s" % self.macTable)

        # Insert flow, deliver packet directly to destination.
        # if packet.dst.is_multicast:
        #     log.debug("Flood multicast from %s", packet.src)
        #     self._drop(event)
        if packet.dst.is_multicast is False and packet.dst in self.macTable:

            out_sw_str, out_port = self.macTable[packet.dst]
            # log.info("%s-->%s" % (src_h_name, dst_h_name))
            self._install_reactive_path(event, out_sw_str, out_port, packet)

            # log.info("sending to entry in mactable: %s %s" % (out_dpid, out_port))
            self.switches[out_sw_str].send_packet_data(out_port, event.data)

        else:
            self._flood(event)

    def _handle_PacketIn(self, event):
        # log.info("Parsing PacketIn.")
        if not self.all_switches_up:
            log.info("Saw PacketIn before all switches were up - ignoring.")
            return
        else:
            if self.mode == 'reactive':
                self._handle_packet_reactive(event)

    def _handle_ConnectionUp(self, event):
        sw_str = self._connToStr(event.connection)
        sw = self.switches.get(sw_str)
        log.info("Saw switch come up: %s", sw_str)
        if sw_str not in self.t.switches():
            log.warn("Ignoring unknown switch %s" % sw_str)
            return
        if sw is None:
            log.info("Added fresh switch %s" % sw_str)
            sw = Switch()
            self.switches[sw_str] = sw
            sw.connect(event.connection)
        else:
            log.info("Odd - already saw switch %s come up" % sw_str)
            sw.connect(event.connection)
        sw.connection.send(of.ofp_set_config(miss_send_len=MISS_SEND_LEN))

        if len(self.switches) == len(self.t.switches()):
            log.info("Woo!  All switches up")
            self.all_switches_up = True


def launch(topo=None, routing=None, mode=None):

    if not mode:
        mode = DEF_MODE
    # Instantiate a topo object from the passed-in file.
    if not topo:
        raise Exception("please specify topo and args on cmd line")
    else:
        t = buildTopo(topo, topos)
        r = getRouting(routing, t)
    core.registerNew(TestBedController, t, r, mode)

    log.info("TestBedController running with topo=%s." % topo)
