import socket
import base64
import threading
import json

class DNSQuery:
  def __init__(self, data):
    self.data = data
    self.data_text = ''

    tipo = (ord(data[2]) >> 3) & 15   # Opcode bits
    if tipo == 0:                     # Standard query
      ini=12
      lon=ord(data[ini])
    while lon != 0:
      self.data_text += data[ini+1:ini+lon+1]+'.'
      ini += lon+1
      lon=ord(data[ini])

  def request(self, ip):
    packet=''
    if self.data_text:
      packet+=self.data[:2] + "\x81\x80"
      packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
      packet+=self.data[12:]                                         # Original Domain Name Question
      packet+='\xc0\x0c'                                             # Pointer to domain name
      packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
      packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
    return packet


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
      w = open('/tmp/json','w')
      w.write(self.r_data)
      w.close()
    
    self.r_data = ''
    self.frame_id=0
    
  def run_once(self):
    data, addr = self.udp.recvfrom(1024)
    self.log.write(data)
    self.log.write("\n")
    
    p=DNSQuery(data)
    req_split = p.data_text.split(".")
    req_split.pop() # fix trailing dot... cba to fix this
    if req_split[1] != self.subdomain:
      return
    tmp = base64.b64decode(req_split[0])
    self.udp.sendto(p.request(self.ip), addr)
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
