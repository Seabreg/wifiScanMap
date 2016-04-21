import ssl
import json
import urllib2
import urllib
import threading
import time


class Synchronizer(threading.Thread):
  def __init__(self, application, uri):
    self.application = application
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true
    self.base = uri
    self.context = ssl._create_unverified_context()

  def synchronize(self, date = None):
    if date is None:
      date = '1980-01-01 00:00:00'
    res = self.application.getAll(date)['networks']
    data = {
      'ap':res,
      'probes': [],
      'stations': []
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "network synced"
    
    res = self.application.getAllProbes()
    data = {
      'ap':[],
      'probes': res,
      'stations': []
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    print "probes synced"
    
    res = self.application.getAllStations('date > "%s"'%date)
    data = {
      'ap':[],
      'probes': [],
      'stations': res
    }
    req = urllib2.Request('%s/upload.json'%self.base)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data), context=self.context)
    
    print "stations synced"
  
  def run(self):
    time.sleep(5)
    while self.running:
      
      try:
        raw = urllib2.urlopen("%s/status.json"%self.base, context=self.context)
        date = json.loads(raw.read())["sync"]
        if date is not None:
          date = date[0].split('.')[0]
        else:
          date = None
        self.synchronize(date)
        
      except:
        print "Sync unavailable"
      time.sleep(60)

  def stop(self):
      self.running = False