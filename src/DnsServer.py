import socket
import base64
import threading
import json
import PrctlTool

## needs scapy 2.3.2
from scapy.all import DNS, DNSQR, DNSRR, dnsqtypes
import scapy.all


class DnsServer(threading.Thread):
  IP_OK = '0.0.0.0'
  IP_ERROR = '1.1.1.1'
  
  def __init__(self, app):
    threading.Thread.__init__(self)
    self.application = app
    self.running = True #setting the thread running to true
    self.r_data = {}
    self.frame_id = {}
    self.ip = '0.0.0.0'
    self.subdomain = 't1'
    self.log = open('/tmp/dns_raw.log','w')
    self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
  def reset(self, _id):
    print "reset %s"%_id
    if not self.r_data.has_key(_id):
      self.r_data[_id] = {}
      
    if self.r_data[_id] != '':
      w = open('/tmp/dns_json_%s'%str(_id),'w')
      d = ''
      for k,v in self.r_data[_id].iteritems():
        d += v
      w.write(d)
      w.close()
    self.r_data[_id] = {}
    self.frame_id[_id]=0
  
  def answer(self, addr, dns, ip):
    query = dns[DNSQR].qname.decode('ascii')
    response = DNS(
    id=dns.id, ancount=1, qr=1,
    qd=dns.qd,
    an=DNSRR(rrname=str(query), type='A', rdata=str(ip), ttl=1234),
    ar=scapy.layers.dns.DNSRROPT(rclass=3000))
    self.udp.sendto(bytes(response), addr)
  
  def run_once(self):
    data, addr = self.udp.recvfrom(1024)
    #print "dns query from %s"%addr[0]
    self.log.write(data)
    self.log.write("\n")
    
    
    dns = DNS(data)
    assert dns.opcode == 0, dns.opcode  # QUERY
    if dnsqtypes[dns[DNSQR].qtype] != 'A':
      return
    #dns.show()
    query = dns[DNSQR].qname.decode('ascii')  # test.1.2.3.4.example.com.
    req_split = query.rsplit('.')

    if req_split[1] != self.subdomain:
      self.application.log('Dns' , 'Wrong subdomain (%s != %s)'%(req_split[1], self.subdomain))
      return
    #self.application.log('Dns' , 'request from %s : %s'%(addr[0], query))
    
    tmp = base64.b64decode(req_split[0])
    #check if sender's id is present
    sender_id = -1

    try:
      data_start = 14
      sender_id = int(tmp[:8])
      frame = int(tmp[8:10])
      rand = int(tmp[10:14])
    except:
      data_start = 2
      frame = int(tmp[:2])
      return # old protocol
      
    if frame == 0:
      self.reset(sender_id)
    
    if not self.frame_id.has_key(sender_id):
      self.frame_id[sender_id] = 0
      
    if not self.r_data.has_key(sender_id):
      self.r_data[sender_id] = {}
      
    self.answer(addr, dns, DnsServer.IP_OK)
    print " received frame %s for %s"%(frame, sender_id)
    if self.r_data[sender_id].has_key(frame):
      print "   frame %s already received"%frame
      return

    
    self.frame_id[sender_id] += 1
      
    self.r_data[sender_id][frame] = tmp[data_start:]
    try:
      d = ''
      for k,v in self.r_data[sender_id].iteritems():
        d += v
      j = json.loads(d)
      self.application.log("Dns %s"%j['n'], "%d ap, %d probes, %d stations"%(len(j['ap']), len(j['p']), len(j['s'])))
      self.application.synchronizer.synchronize_esp8266(j)
    except ValueError as e:
      pass
      
    
  def run(self):
    PrctlTool.set_title('dns server')
    try:
      self.udp.bind((self.ip,53))
    except:
      self.application.log('Dns' , 'cannot bind to %s:53'%self.ip)
      return
    self.application.log('Dns' , 'starting..')
    while self.running:
      try: 
        self.run_once()
      except Exception as e:
        self.application.log('Dns' , 'Exception %s..'%e)
