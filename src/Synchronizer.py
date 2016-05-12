import ssl
import json
import urllib2
import urllib
import threading
import time
import socket


class Synchronizer(threading.Thread):
  def __init__(self, application, uri):
    self.esp8266 = {}
    self.application = application
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true

    self.base = uri
    self.hostname = socket.gethostname()
    self.context = ssl._create_unverified_context()

  def update(self, hostname, entity, date = None):
    if date is None:
      date = 'CURRENT_TIMESTAMP'
    else:
      date = '"%s"'%date
    q = '''select * from sync where hostname="%s" and entity="%s"'''%(hostname, entity)
    res = self.application.fetchone(q)
    if res is not None:
      q = '''update sync set date = %s where hostname="%s" and entity="%s"'''%(date, hostname, entity)
    else:
      q = '''insert into sync (hostname, entity, date) values ("%s", "%s", CURRENT_TIMESTAMP) '''%(hostname, entity)
    self.application.query(q)
    self.application.commit()

  def update_position(self, hostname, position):
    q = '''select * from devices where hostname="%s"'''%hostname
    res = self.application.fetchone(q)
    if res is not None:
      q = '''update devices set date = %s, latitude=%s, longitude=%s, source="%s" where hostname="%s" '''%('CURRENT_TIMESTAMP', position['latitude'], position['longitude'], position['source'], hostname)
    else:
      q = '''insert into devices (hostname, latitude, longitude, source, date) values ("%s", "%s", "%s", "%s", CURRENT_TIMESTAMP) '''%(hostname, position['latitude'], position['longitude'], position['source'])
    self.application.query(q)
    self.application.commit()

  def syncronize_position(self):
    pos = self.application.getPosition()
    if pos is not None:
      data = {
        'hostname': self.hostname,
        'ap':[],
        'probes': [],
        'stations': [],
        'bt_stations': [],
        'position': {
          'latitude': pos[1],
          'longitude': pos[0],
          'source': pos[2],
          }
      }
      
      req = urllib2.Request('%s/upload.json'%self.base)
      req.add_header('Content-Type', 'application/json')
      response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=False), context=self.context)
      self.application.log('Sync',"Position synced")
      return True
    return True

  def synchronize_ap(self, date = None):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAll(date)['networks']
    data = {
      'hostname': self.hostname,
      'ap':res,
      'probes': [],
      'stations': [],
      'bt_stations': [],
      'position': None
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=False), context=self.context)
    self.application.log('Sync',"network synced")
    return True
  
  def synchronize_probes(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAllProbes()
    data = {
      'hostname': self.hostname,
      'ap':[],
      'probes': res,
      'stations': [],
      'bt_stations': [],
      'position': None
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=False), context=self.context)
    self.application.log('Sync',"probes synced")
    return True
  
  def synchronize_stations(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAllStations('date > "%s"'%date)
    data = {
      'hostname': self.hostname,
      'ap':[],
      'probes': [],
      'stations': res,
      'bt_stations': [],
      'position': None
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=False), context=self.context)
    self.application.log('Sync',"stations synced")
    return True
  
  def synchronize_bt_stations(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAllBtStations('date > "%s"'%date)
    data = {
      'hostname': self.hostname,
      'ap':[],
      'probes': [],
      'stations': [],
      'bt_stations': res,
      'position': None
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data, ensure_ascii=False), context=self.context)
    self.application.log('Sync',"bt stations synced")
    return True
  
  def synchronize_data(self, data):
    hostname = data['hostname']
      
    if data['position'] is not None:
      self.update_position(hostname, data['position'])
    
    for n in data['ap']:
      network = {}
      network['bssid'] = n[0]
      network['essid'] = n[1]
      network['encryption'] = n[2]
      network['signal'] = n[3]
      network['longitude'] = n[4]
      network['latitude'] = n[5]
      network['frequency'] = n[6]
      network['channel'] = n[7]
      network['mode'] = n[8]
      network['date'] = n[9]
      network['gps'] = n[10]
      self.application.update(network)
      self.update(hostname, 'ap', network['date'])
    
    for probe in data['probes']:
      self.application.update_probe(probe)
      self.update(hostname, 'probes', probe['date'])
    
    for station in data['stations']:
      self.application.update_station(station)
      self.update(hostname, 'stations', station['date'])
    
    for station in data['bt_stations']:
      self.application.update_bt_station(station)
      self.update(hostname, 'bt_stations', station['date'])
  
  def synchronize_esp8266(self, data):
    self.application.log('Sync esp8266',"synchro")
    hostname = data['hostname']
    
    position = None
    if data.has_key("ap") and len(data["ap"]) > 0:
      self.esp8266[hostname] = self.application.getWifiPosition(data["ap"])
    if self.esp8266.has_key(hostname):
      position = self.esp8266[hostname]
    else:
      self.application.log('Sync esp8266',"Position unavailable")
    
    if position is None:
      return False
    
    self.update_position(hostname, {'latitude':position[0], 'longitude':position[1], 'source':'wifi' })
    
    aps = 0
    try:
      for n in data['ap']:
        n['longitude'] = position[1]
        n['latitude'] = position[0]
        n['frequency'] = '""'
        n['mode'] = 'Master'
        n['gps'] = False
        self.application.update(n)
        self.update(hostname, 'ap' )
        aps += 1
    except:
      self.application.log('Sync esp8266',"ap update fail")
    
    probes = 0
    try:
      for probe in data['probes']:
        self.application.update_probe(probe)
        self.update(hostname, 'probes')
        probes += 1
    except:
      self.application.log('Sync esp8266',"probe update fail")
    
    try:
      stations = 0
      for station in data['stations']:
        self.application.update_station(station)
        self.update(hostname, 'stations')
        stations += 1
    except:
      self.application.log('Sync esp8266',"stations update fail")
      
    self.application.log('Sync %s'%hostname,"%d aps, %d probes, %d stations"%(aps, probes, stations))
  
  def run(self):
    time.sleep(5)
    while self.running:
      delay = 60*10
      try:
        raw = urllib2.urlopen("%s/sync.json?hostname=%s"%(self.base, self.hostname), context=self.context)
        data = json.loads(raw.read())
        
        date_ap = None
        date_probes = None
        date_stations = None
        date_bt_stations = None
        
        try:
          date_ap = data['ap'].split('.')[0]
        except:
          pass
        
        try:
          date_probes = data['probes'].split('.')[0]
        except:
          pass
        
        try:
          date_stations = data['stations'].split('.')[0]
        except:
          pass
        
        try:
          date_bt_stations = data['bt_stations'].split('.')[0]
        except:
          pass
        
        self.syncronize_position()
        self.synchronize_ap(date_ap)
        self.synchronize_probes(date_probes)
        self.synchronize_stations(date_stations)
        self.synchronize_bt_stations(date_bt_stations)
          
      except:
        self.application.log('Sync',"Sync unavailable")
        delay = 30
      time.sleep(delay)

  def stop(self):
      self.running = False