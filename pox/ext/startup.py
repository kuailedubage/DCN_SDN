# Put me in ext/startup.py
 
def launch ():
  from log.level import launch
  launch(DEBUG=True)
 
  from samples.pretty_log import launch
  launch()
 
  from openflow.keepalive import launch
  launch(interval=15) # 15 seconds
 
  from forwarding.l2_pairs import launch
  launch()
