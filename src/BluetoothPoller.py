from threading import Lock
import threading
import time
import subprocess
import re

class BluetoothPoller(threading.Thread):
  def __init__(self, app):
    threading.Thread.__init__(self)
    self.application = app
    self.lock = Lock()
    self.stations = []
    self.running = True #setting the thread running to true
    
    if self.application.args.sleep is not None:
      self.sleep = int(self.application.args.sleep)
    else:
      self.sleep = 1
  
  def run(self):
    try:
      while self.running:
        cmd = ['hcitool', 'inq']
        pos = self.application.getPosition()
        fix = pos is not None
        if fix:
          lon, lat, source = pos
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        (stdoutdata, stderrdata) = process.communicate();
        res = re.findall("\s(.*)\sclock.*\sclass:\s(.*)", stdoutdata)
        stations = []
        if res is not None:
          for row in res:
            station = {}
            if fix:
              station["latitude"] = lat
              station["longitude"] = lon
              station["gps"] = source == 'gps'
            station['bssid'] = row[0].strip()
            station['manufacturer'] = self.application.getManufacturer(station['bssid'])
            station['class'] = int(row[1].strip(), 0)
            cmd = ['hcitool', 'name', station['bssid']]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            (stdoutdata, stderrdata) = process.communicate();
            station['name'] = stdoutdata
            stations.append(station)
    
        with self.lock:
          self.stations = stations
        time.sleep(self.sleep)
    except:
      self.application.log('bluetooth', 'error')
        
  def getNetworks(self):
    with self.lock:
      return self.networks
          
  def stop(self):
      self.running = False