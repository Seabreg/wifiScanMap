from threading import Lock
import threading
import time
import subprocess
import re
import PrctlTool

class BluetoothPoller(threading.Thread):
  def __init__(self, app):
    threading.Thread.__init__(self)
    self.application = app
    self.lock = Lock()
    self.stations = []
    self.running = True #setting the thread running to true
    
    self.major_device_description = {
      0b00000: 'miscalleneous',
      0b00001: 'computer',
      0b00010: 'mobile',
      0b00011: 'lan',
      0b00100: 'audio',
      0b00101: 'peripheral',
      0b00110: 'imaging',
      0b00111: 'wearable',
      0b01000: 'toy',
      0b01001: 'health',
      0b11111: 'unknown',
      }
    
    if self.application.args.sleep is not None:
      self.sleep = int(self.application.args.sleep)
    else:
      self.sleep = 1
  
  def parse_class(self,  _class):
    return (_class >> 8 & 0b0000000000011111)
  
  def get_major_device_description(self, major):
    try:
      return self.major_device_description[major]
    except:
      self.application.log('bluetooth', 'invalid class %s'%major)
  
  def run(self):
    PrctlTool.set_title('bluetooth poller')
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
            station['class_description'] = self.get_major_device_description(self.parse_class(station['class']))
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