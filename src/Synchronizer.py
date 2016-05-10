import ssl
import json
import urllib2
import urllib
import threading
import time
import socket


class Synchronizer(threading.Thread):
  def __init__(self, application, uri):
    self.application = application
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true

    self.base = uri
    self.hostname = socket.gethostname()
    self.context = ssl._create_unverified_context()

  def update(self, hostname, entity, date):
    q = '''select * from sync where hostname="%s" and entity="%s"'''%(hostname, entity)
    res = self.application.fetchone(q)
    if res is not None:
      q = '''update sync set date = "%s" where hostname="%s" and entity="%s"'''%(date, hostname, entity)
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