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
    self.r_data = ''
    self.frame_id = 0
    self.ip = '0.0.0.0'
    self.subdomain = 't1'
    self.log = open('/tmp/dns_raw.log','w')
    self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
  def reset(self):
    if self.r_data != '':
      w = open('/tmp/dns_json','w')
      w.write(self.r_data)
      w.close()
    
    self.r_data = ''
    self.frame_id=0
  
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
    data_start = tmp.find('{')
    if data_start == 2:
      sender_id = tmp[:4]
      frame = int(tmp[4:6])
    else:
      frame = int(tmp[:2])
    
    if frame == 0:
      self.reset()
    # frame may be < self.frame_id as several dns server make request at the same time
    if frame > self.frame_id:
      self.application.log('Dns' , 'should receive %d but received %d from %s'%(self.frame_id, frame, addr[0]))
      self.answer(addr, dns, DnsServer.IP_ERROR)
      return
    if frame < self.frame_id:
      #already received frame
      return
    
    self.answer(addr, dns, DnsServer.IP_OK)
    self.frame_id += 1
    self.r_data += tmp[data_start:]
    print "========"
    print self.r_data
    try:
      d = self.r_data.strip()
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
      #try: 
      self.run_once()
      #except Exception as e:
        #self.application.log('Dns' , 'Exception %s..'%e)
