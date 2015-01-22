# Copyright 2011-2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This component blocks the domain names 
 
Run along with l2_learning.
 
You can specify names to block on the commandline:
./pox.py forwarding.l2_learning dns_block --domain_names=www.baidu.com,www.hao123.com
 
Alternatively, if you run with the "py" component, you can use the CLI:
./pox.py forwarding.l2_learning dns_block py
 ...
POX> block("www.baidu.com", "www.google.com")
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
import pox.lib.packet.dns as pkt_dns
from pox.lib.addresses import IPAddr
from pox.lib.revent import *

log = core.getLogger()
# A set of domain names to block
blacklist = set()


class DNSBlock (EventMixin):

  def __init__(self):
    
    core.openflow.addListeners(self) 
  
  def _handle_ConnectionUp(self, event):
      msg = of.ofp_flow_mod()
      msg.match = of.ofp_match()
      msg.match.dl_type = pkt.ethernet.IP_TYPE
      msg.match.nw_proto = pkt.ipv4.UDP_PROTOCOL
      msg.match.tp_src = 53
      msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
      event.connection.send(msg)

  def _handle_PacketIn (self, event):
    p = event.parsed.find('dns')

    if p is not None and p.parsed:
      log.debug(p)

      for q in p.questions:
        if q.name in blacklist:
	   event.halt = True
           return


def unblock(*domain_names):
    print domain_names
    blacklist.difference_update(domain_names)
    print blacklist


def block(*domain_names):
    print domain_names
    blacklist.update(domain_names)
    print blacklist


def launch(domain_names=''):
    # Add names from commandline to list of domain names to block
    blacklist.update(str(x) for x in domain_names.replace(",", " ").split())
    print blacklist
    # Add functions to Interactive so when you run POX with py, you
    # can easily add/remove domain names to blacklist.
    core.Interactive.variables['block'] = block
    core.Interactive.variables['unblock'] = unblock
    core.registerNew(DNSBlock)
