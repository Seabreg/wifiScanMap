import ssl
import json
import urllib2
import urllib
import threading
import time
import socket
from threading import Lock
import PrctlTool

class Synchronizer(threading.Thread):
  def __init__(self, application, uri):
    self.lock = Lock()
    self.esp8266 = {}
    self.sync_running = {}
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
      q = '''update sync set date = %s where hostname="%s" and entity="%s" and date < %s'''%(date, hostname, entity, date)
    else:
      q = '''insert into sync (hostname, entity, date) values ("%s", "%s", CURRENT_TIMESTAMP) '''%(hostname, entity)
    self.application.query(q)
    self.application.commit()

  def update_position(self, hostname, position):
    q = '''select * from devices where hostname="%s" and latitude=%s and longitude=%s'''%(hostname,position['latitude'], position['longitude'])
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
      response.read()
      self.application.log('Sync',"Position synced")
      return True
    return True

  def synchronize_ap(self, date = None):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAll(None, None,date)['networks']
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
    response.read()
    self.application.log('Sync',"%s network synced from %s"%(len(res), date))
    return True
  
  def synchronize_probes(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getSyncProbes(date)
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
    response.read()
    self.application.log('Sync',"%s probes synced from %s"%(len(res),date))
    return True
  
  def synchronize_stations(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAllStations('date > "%s" order by date asc'%date)

    self.application.log('Sync',"%s stations to be synced %s"%(len(res),date))

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
    print "====================>"
    try:
      print response.read()
    except Exception as e:
      print e
      
    print "<===================="
    self.application.log('Sync',"%s stations synced %s"%(len(res),date))
    return True
  
  def synchronize_bt_stations(self, date):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAllBtStations('date > "%s" order by date asc'%date)
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
    response.read()
    self.application.log('Sync',"%s bt stations synced from %s"%(len(res), date))
    return True
  
  def synchronize_data(self, data):
    hostname = data['hostname']
    with self.lock:
      if self.sync_running.has_key(hostname) and self.sync_running[hostname]:
        return
      
      self.sync_running[hostname] = True
      
    if data['position'] is not None:
      self.update_position(hostname, data['position'])
    
    self.application.log('Sync',"sync %s: %d ap, %d probes, %d stations, %d bt_stations"%(hostname, len(data['ap']), len(data['probes']), len(data['stations']), len(data['bt_stations'])))
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
      
    with self.lock:
      self.sync_running[hostname] = False
  
  def get_esp8266_data(self):
    with self.lock:
      return self.esp8266
    
  def synchronize_esp8266(self, data):
    with self.lock:
      self.application.log('Sync esp8266',"synchro")
      hostname = data['n']
      
      position = None
      if data.has_key("ap") and len(data["ap"]) > 0:
        wifis = []
        for w in data["ap"]:
          wifis.append({'bssid': w['b'], 'essid': w['e']})
        if not self.esp8266.has_key(hostname):
          self.esp8266[hostname] = {}
        self.esp8266[hostname]['current'] = {}
        wifi_pos = self.application.getWifiPosition(wifis)
        if wifi_pos is not None:
          self.application.log('Sync esp8266',"Position from wifis %s,%s"%(wifi_pos[0], wifi_pos[1]))
        if wifi_pos is not None:
          self.esp8266[hostname]['position'] = wifi_pos
      if self.esp8266[hostname].has_key('position'):
        position = self.esp8266[hostname]['position']
      
      if position is None:
        self.application.log('Sync esp8266',"Position unavailable")
        return False
      
      self.update_position(hostname, {'latitude':position[0], 'longitude':position[1], 'source':'wifi' })

      
      
      networks = []
      try:
        for n in data['ap']:
          network = {}
          network['bssid'] = n['b']
          network['essid'] = n['e']
          network['encryption'] = n['k']
          network['signal'] = int(n['s'])
          network['longitude'] = position[1]
          network['latitude'] = position[0]
          network['frequency'] = '""'
          network['channel'] = n['c']
          network['mode'] = 'Master'
          network['gps'] = False
          self.application.update(network)        
          self.update(hostname, 'ap' )
          networks.append(network);
      except:
        self.application.log('Sync esp8266',"ap update fail")
      
      self.esp8266[hostname]['current']['wifis'] = networks
      
      probes = []
      try:
        for p in data['p']:
          probe = {}
          probe['bssid'] = p['b']
          probe['essid'] = p['e']
          self.application.update_probe(probe)
          probes.append(probe)
          self.update(hostname, 'probes')
      except:
        self.application.log('Sync esp8266',"probe update fail")
      
      self.esp8266[hostname]['current']['probes'] = probes
      
      stations = []
      try:
        for s in data['s']:
          station = {}
          station['bssid'] = s['b']
          station['signal'] = int(s['s'])
          station['longitude'] = position[1]
          station['latitude'] = position[0]
          self.application.update_station(station)
          stations.append(station)
          self.update(hostname, 'stations')
      except:
        self.application.log('Sync esp8266',"stations update fail")
        
      self.esp8266[hostname]['current']['stations'] = stations
      
      self.application.log('Sync %s'%hostname,"%d aps, %d probes, %d stations"%(len(networks), len(probes), len(stations)))
  
  
  def get_sync(self, hostname):
    sync = {}
    sync['date'] = {}
    q = '''select * from sync where hostname="%s"'''%hostname
    res = self.application.fetchall(q)
    if res is not None:
      for r in res:
        sync['date'][r[1]] = r[2]
    
    sync_status = False
    with self.lock:
      if self.sync_running.has_key(hostname):
        sync_status = self.sync_running[hostname]
    sync['syncing'] = sync_status
    return sync
  
  def run(self):
    PrctlTool.set_title('synchronizer')
    time.sleep(5)
    while self.running:
      delay = 60*10
      try:
        raw = urllib2.urlopen("%s/sync.json?hostname=%s"%(self.base, self.hostname), context=self.context)
        data = json.loads(raw.read())

        if not data['syncing']:
          date_ap = None
          date_probes = None
          date_stations = None
          date_bt_stations = None
          
          try:
            date_ap = data['date']['ap'].split('.')[0]
          except:
            pass
          
          try:
            date_probes = data['date']['probes'].split('.')[0]
          except:
            pass
          
          try:
            date_stations = data['date']['stations'].split('.')[0]
          except:
            pass
          
          try:
            date_bt_stations = data['date']['bt_stations'].split('.')[0]
          except:
            pass
          
          self.syncronize_position()
          self.synchronize_ap(date_ap)
          self.synchronize_probes(date_probes)
          self.synchronize_stations(date_stations)
          self.synchronize_bt_stations(date_bt_stations)
        else:
          self.application.log('Sync',"already syncing")
          
      except:
        self.application.log('Sync',"Sync unavailable")
        delay = 30
      time.sleep(delay)

  def stop(self):
      self.running = False

