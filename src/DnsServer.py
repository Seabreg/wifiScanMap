import socket
import base64
import threading
import json
import PrctlTool

## needs scapy 2.3.2
from scapy.all import DNS, DNSQR, DNSRR, dnsqtypes
import scapy.all


class DnsServer(threading.Thread):
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
    
  def run_once(self):
    data, addr = self.udp.recvfrom(1024)
    #print "dns query from %s"%addr[0]
    self.log.write(data)
    self.log.write("\n")
    
    
    dns = DNS(data)
    assert dns.opcode == 0, dns.opcode  # QUERY
    if dnsqtypes[dns[DNSQR].qtype] != 'A':
      return
    dns.show()
    query = dns[DNSQR].qname.decode('ascii')  # test.1.2.3.4.example.com.
    req_split = query.rsplit('.')
    
    print req_split


    if req_split[1] != self.subdomain:
      self.application.log('Dns' , 'Wrong subdomain (%s != %s)'%(req_split[1], self.subdomain))
      return
    
    response = DNS(
        id=dns.id, ancount=1, qr=1,
        qd=dns.qd,
        an=DNSRR(rrname=str(query), type='A', rdata=str(self.ip), ttl=1234),
        ar=scapy.layers.dns.DNSRROPT(rclass=3000))
    
    self.udp.sendto(bytes(response), addr)

    
    
    tmp = base64.b64decode(req_split[0])
    frame = int(tmp[:2])
    if frame == 0:
      self.reset()
    if frame != self.frame_id:
      self.application.log('Dns' , 'should receive %d but received %d'%(self.frame_id, frame))
      return
    self.frame_id += 1
    self.r_data += tmp[2:]
    try:
      d = self.r_data.strip()
      j = json.loads(d)
      self.application.log("Dns %s"%j['n'], "%d ap, %d probes, %d stations"%(len(j['ap']), len(j['p']), len(j['s'])))
      self.application.synchronizer.synchronize_esp8266(j)
    except Exception as e:
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
