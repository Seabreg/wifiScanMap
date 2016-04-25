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

  def synchronize_ap(self, date = None):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAll(date)['networks']
    data = {
      'hostname': self.hostname,
      'ap':res,
      'probes': [],
      'stations': [],
      'bt_stations': []
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "network synced"
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
      'bt_stations': []
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "probes synced"
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
      'bt_stations': []
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "stations synced"
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
      'bt_stations': res
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "bt stations synced"
    return True
  
  def run(self):
    time.sleep(5)
    while self.running:
      
      #try:
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
      
      self.synchronize_ap(date_ap)
      self.synchronize_probes(date_probes)
      self.synchronize_stations(date_stations)
      self.synchronize_bt_stations(date_bt_stations)
        
      #except:
        #print "Sync unavailable"
      time.sleep(60)

  def stop(self):
      self.running = False