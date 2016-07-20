import subprocess
import os
import threading
from threading import Lock
import datetime
import time
import sys
import shutil
import PrctlTool

default_airodump_age = 5

class AirodumpPoller(threading.Thread):
  def __init__(self, app):
    threading.Thread.__init__(self)
    self.application = app
    self.run_for = 60*60 # 1 hour
    self.lock = Lock()
    self.networks = []
    self.stations = []
    self.probes = []
    self.running = True #setting the thread running to true
    self.error_id = 0
    self.start_date = None
    self.sleep = 1
    try:
      if self.application.args.sleep is not None:
        self.sleep = int(self.application.args.sleep)
    except:
      pass

  def is_mac_valid(self, mac):
    return len(mac) == 17

  def date_from_str(self, _in):
    return datetime.datetime.strptime(_in.strip(), '%Y-%m-%d %H:%M:%S')
  
  def is_too_old(self, date, sleep):
    diff = datetime.datetime.now() - self.date_from_str(date)
    return diff.total_seconds() > sleep
  
  def parse_wifi(self, fields, check_age = True):
    if len(fields) >= 13:
      if(fields[0] != 'BSSID'):
        n = {}
        try:
          n["bssid"] = fields[0]
          n["essid"] = fields[13].replace("\r\n", "")
          n["mode"] = 'Master'
          n["channel"] = fields[3]
          n["frequency"] = -1
          n["signal"] = float(fields[8])
          
          if(n["signal"] >= -1):
            n["signal"] = -100
          
          n["encryption"] = fields[5].strip() != "OPN"
          if not check_age or not self.is_too_old(fields[2], default_airodump_age):
            if self.is_mac_valid(n["bssid"]):
              return n
        except Exception as e:
          backup = True
          self.application.log("wifi", 'parse fail')
          exc_type, exc_obj, exc_tb = sys.exc_info()
          fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
          print(exc_type, fname, exc_tb.tb_lineno)
          self.application.log('airodump' , fields)
          self.application.log('airodump' , n)
    return None
  
  def process_csv(self, csv_path, check_age = True):
    backup = False
    res = {'wifis':[], 'probes':[], 'stations':[]}
    f = open(csv_path)
    for line in f:
      fields = line.split(', ')
      wifi = self.parse_wifi(fields, check_age)
      if wifi is not None:
        res['wifis'].append(wifi)     
      elif len(fields) == 7 or len(fields) == 6:
        try:
          if(fields[0] != 'Station MAC'):
            s = {}
            s['bssid'] = fields[0]
            s['last_seen'] = fields[2]
            s['signal'] = float(fields[3])
            
            if not check_age or not self.is_too_old(fields[2], default_airodump_age):
              if self.is_mac_valid(s['bssid']):
                res['stations'].append(s)
            
            if len(fields) == 7:
              for r in fields[6].split(','):
                p = {}
                p['bssid'] = fields[0]
                p['signal'] = s['signal']
                p['essid'] = r.replace("\r\n", "")
                if p['essid'] != "":
                  if not check_age or not self.is_too_old(s['last_seen'], default_airodump_age):
                    if self.is_mac_valid(p['bssid']):
                      res['probes'].append(p)
        except Exception as e:
          backup = True
          self.application.log("wifi", 'station parse fail')
          exc_type, exc_obj, exc_tb = sys.exc_info()
          fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
          print(exc_type, fname, exc_tb.tb_lineno)
          self.application.log('airodump' , line)
          
    f.close()
    if backup and self.application.args.log:
      shutil.copyfile(csv_path, "/tmp/wifimap-%s.csv"%self.error_id)
      self.error_id += 1
      
    return res
  
  def run(self):
    PrctlTool.set_title('airodump poller')
    while self.running:
      self.application.log('airodump' , 'starting..')
      self.run_once()
      time.sleep(self.sleep)
  
  def run_more(self):
    return ( datetime.datetime.now() - self.start_date).total_seconds() < self.run_for  
  
  def run_once(self):
    self.start_date = datetime.datetime.now()
    FNULL = open(os.devnull, 'w')
    prefix= '/tmp/wifi-dump'
    os.system("rm %s*"%prefix)
    cmd = ['airodump-ng', '-w', prefix,  '--berlin', str(self.sleep), self.application.interface]
    process = subprocess.Popen(cmd, stdout=FNULL, stdin=FNULL, stderr=FNULL)
    f = open("/var/run/wifimap-airodump", 'w')
    f.write('%s'%process.pid)
    f.close()
    
    time.sleep(10)
    #['BSSID', ' First time seen', ' Last time seen', ' channel', ' Speed', ' Privacy', ' Cipher', ' Authentication', ' Power', ' # beacons', ' # IV', ' LAN IP', ' ID-length', ' ESSID', ' Key']
    error_id = 0
    while self.running and self.run_more():
      pos = self.application.getPosition()
      fix = pos is not None
      if fix:
        lon, lat, source = pos
      wifis = []
      stations = []
      probes = []
      
      csv_path = "%s-01.csv"%prefix
      res = self.process_csv(csv_path)
      for wifi in res['wifis']:
        w = wifi
        w['manufacturer'] = self.application.getManufacturer(w["bssid"])
        w['mobile'] = self.application.is_mobile(w["manufacturer"])
        if fix:
          w["latitude"] = lat
          w["longitude"] = lon
          w["gps"] = 0
          if source == 'gps':
            w["gps"] = 1
        if w['bssid'] not in self.application.ignore_bssid:
          wifis.append(w)
      
      for probe in res['probes']:
        p = probe
        p['manufacturer'] = self.application.getManufacturer(p['bssid'])
        p['mobile'] = self.application.getManufacturer(p['manufacturer'])
        p['ap'] = self.application.getWifisFromEssid(p['essid'])
        if p['bssid'] not in self.application.ignore_bssid:
          probes.append(p)
          
          
      for station in res['stations']:
        s = station
        s['manufacturer'] = self.application.getManufacturer(s['bssid'])
        s['mobile'] = self.application.is_mobile(s['manufacturer'])
        s['users_dns'] = self.application.getUsersDns(s['bssid'])
        if fix:
          s['latitude'] = lat
          s['longitude'] = lon
        if s['bssid'] not in self.application.ignore_bssid:
          stations.append(s)
          
      with self.lock:
        self.networks = wifis
        self.stations = stations
        self.probes = probes
      time.sleep(self.sleep/2.)
    process.kill()
        
  def getNetworks(self):
    with self.lock:
      return self.networks
          
  def stop(self):
      self.running = False
      
if __name__ == '__main__':
  ap = AirodumpPoller(None)
  for path in sys.argv[1:len(sys.argv)]:
    print ap.process_csv(path, False)