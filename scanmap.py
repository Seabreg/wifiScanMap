#!/usr/bin/env python

import subprocess
import threading
from threading import Lock
import time
from gps import *
import os
import sys
from os import path
import commands
import argparse
import re
import json
import sqlite3
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from threading import Thread
import json
import urllib2
import urllib
import ssl
import shutil
from math import radians, cos, sin, asin, sqrt

import datetime

#meters
min_gpsd_accuracy = 30
default_airodump_age = 5

try:
  import RPi.GPIO as GPIO
  GPIO.setmode(GPIO.BCM) 
except:
  print "No gpio"

USE_SCAPY=False

if(USE_SCAPY):
  from scapy.all import *
  from scapy_ex import *
else:
  import csv
  
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", help="wifi interface")    
    parser.add_argument("-s", "--sleep", help="wifi interface")  
    parser.add_argument("-d", "--database", help="wifi database")
    parser.add_argument('-w', '--www', help='www port')
    parser.add_argument('-a', '--accuracy', help='minimum accuracy')
    parser.add_argument('-u', '--synchro', help='synchro uri ie http://test.com:8686')
    parser.add_argument('-e', '--enable', action='store_true', help='enable db synchro through json')
    parser.add_argument('-m', '--monitor', action='store_true', help='use monitor mode instead of iwlist')
    parser.add_argument('-b', '--bssid', help='ignore bssid', action='append', nargs='*')
    return parser.parse_args()


class GpsPoller(threading.Thread):
  def __init__(self, gpsd, app):
    threading.Thread.__init__(self)
    self.gpsd = gpsd
    self.application = app
    self.date = False
    self.running = True #setting the thread running to true
    self.gpio = 17
    self.epx = 100
    self.epy = 100
    
    try:
      GPIO.setup(self.gpio, GPIO.OUT, initial=GPIO.LOW)
    except:
      pass

  def run(self):
    while self.running:
      self.gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
      TIMEZ = 0 
      if self.gpsd.utc != None and self.gpsd.utc != '' and not self.date:
        self.date = True
        tzhour = int(self.gpsd.utc[11:13])+TIMEZ
        if (tzhour>23):
          tzhour = (int(self.gpsd.utc[11:13])+TIMEZ)-24
        gpstime = self.gpsd.utc[0:4] + self.gpsd.utc[5:7] + self.gpsd.utc[8:10] + ' ' + str(tzhour) + self.gpsd.utc[13:19]
        print 'Setting system time to GPS time...'
        os.system('sudo date --set="%s"' % gpstime)
      if self.has_fix:
        self.epx = self.gpsd.fix.epx
        self.epy = self.gpsd.fix.epy
        try:
          GPIO.output(self.gpio, GPIO.HIGH)
        except:
          pass
        q = 'insert into gps (latitude, longitude) values ("%s", "%s")'%(self.gpsd.fix.latitude, self.gpsd.fix.longitude)
        self.application.query(q)
      else:
        try:
          GPIO.output(self.gpio, GPIO.LOW)
        except:
          pass
  def getPrecision(self):
    return max(self.epx, self.epy)

  def has_fix(self, accurate = True):
    fix = self.gpsd.fix.mode > 1
    if( accurate ):
      fix = fix and self.epx < self.application.args.accuracy and self.epy < self.application.args.accuracy
    return fix
  
  def stop(self):
      self.running = False
    
class AirodumpPoller(threading.Thread):
  def __init__(self, app):
    threading.Thread.__init__(self)
    self.application = app
    self.lock = Lock()
    self.networks = []
    self.stations = []
    self.probes = []
    self.running = True #setting the thread running to true
    
    if self.application.args.sleep is not None:
      self.sleep = int(self.application.args.sleep)
    else:
      self.sleep = 1

  def date_from_str(self, _in):
    return datetime.datetime.strptime(_in.strip(), '%Y-%m-%d %H:%M:%S')
  
  def is_too_old(self, date, sleep):
    diff = datetime.datetime.now() - self.date_from_str(date)
    return diff.total_seconds() > sleep
  
  def run(self):            
    FNULL = open(os.devnull, 'w')
    prefix= 'wifi-dump'
    os.system("rm wifi-dump*")
    cmd = ['airodump-ng', '-w', prefix,  '--berlin', str(self.sleep), self.application.interface]
    process = subprocess.Popen(cmd, stderr=FNULL)
    f = open("/var/run/wifimap-airodump", 'w')
    f.write('%s'%process.pid)
    f.close()
    
    time.sleep(10)
    #['BSSID', ' First time seen', ' Last time seen', ' channel', ' Speed', ' Privacy', ' Cipher', ' Authentication', ' Power', ' # beacons', ' # IV', ' LAN IP', ' ID-length', ' ESSID', ' Key']
    error_id = 0
    while self.running:
      pos = self.application.getPosition()
      fix = pos is not None
      if fix:
        lon, lat, source = self.application.getPosition()
      wifis = []
      stations = []
      probes = []
      csv_path = "%s-01.csv"%prefix
      f = open(csv_path)
      for line in f:
        fields = line.split(', ')
        if len(fields) >= 13:
          if(fields[0] != 'BSSID'):
            n = {}
            try:
              if fix:
                n["latitude"] = lat
                n["longitude"] = lon
                n["gps"] = 0
                if source == 'gps':
                  n["gps"] = 1
              n["bssid"] = fields[0]
              n["essid"] = fields[13].replace("\r\n", "")
              n["mode"] = 'Master'
              n["channel"] = fields[3]
              n["frequency"] = -1
              n["manufacturer"] = self.application.getManufacturer(n["bssid"])
              n["mobile"] = self.application.is_mobile(n["manufacturer"])
              n["signal"] = float(fields[8])
              
              if(n["signal"] >= -1):
                n["signal"] = -100
              
              n["encryption"] = fields[5].strip() != "OPN"
              if not self.is_too_old(fields[2], default_airodump_age):
                if n["bssid"] not in self.application.ignore_bssid:
                  wifis.append(n)
            except Exception as e:
              self.application.log("wifi", 'parse fail')
              exc_type, exc_obj, exc_tb = sys.exc_info()
              fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
              print(exc_type, fname, exc_tb.tb_lineno)
              self.application.log('airodump' , fields)
              self.application.log('airodump' , n)
              shutil.copyfile(csv_path, "/tmp/wifimap-%s.csv"%error_id)
              error_id += 1
        elif len(fields) == 7 or len(fields) == 6:
          try:
            if(fields[0] != 'Station MAC'):
              s = {}
              s['bssid'] = fields[0]
              s['last_seen'] = fields[2]
              s['signal'] = float(fields[3])
              s["manufacturer"] = self.application.getManufacturer(s["bssid"])
              s["mobile"] = self.application.is_mobile(s["manufacturer"])
              if fix:
                s['latitude'] = lat
                s['longitude'] = lon
              
              if not self.is_too_old(fields[2], default_airodump_age):
                stations.append(s)
              
              if len(fields) == 7:
                for r in fields[6].split(','):
                  p = {}
                  p['bssid'] = fields[0]
                  p['signal'] = s['signal']
                  p['manufacturer'] = s["manufacturer"]
                  p['mobile'] = s['mobile']
                  p['essid'] = r.replace("\r\n", "")
                  if p['essid'] != "":
                    p['ap'] = len(self.application.getWifisFromEssid(p['essid']))
                    if not self.is_too_old(s['last_seen'], default_airodump_age):
                      probes.append(p)
          except:
            self.application.log("wifi", 'station parse fail')
      f.close()
      with self.lock:
        self.networks = wifis
        self.stations = stations
        self.probes = probes
      time.sleep(self.sleep/2)
        
  def getNetworks(self):
    with self.lock:
      return self.networks
          
  def stop(self):
      self.running = False

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
        
  def getNetworks(self):
    with self.lock:
      return self.networks
          
  def stop(self):
      self.running = False


class Synchronizer(threading.Thread):
  def __init__(self, application, uri):
    self.application = application
    threading.Thread.__init__(self)
    self.running = True #setting the thread running to true
    self.base = uri

  def run(self):
    time.sleep(5)
    while self.running:
      
      try:
        context = ssl._create_unverified_context()
        raw = urllib2.urlopen("%s/status.json"%self.base, context=context)
        date = json.loads(raw.read())["sync"]
        if date is not None:
          date = date[0].split('.')[0]
        else:
          date = '1980-01-01 00:00:00'
        
        res = self.application.getAll(date)['networks']
        data = {
          'ap':res,
          'probes': [],
          'stations': []
        }
        req = urllib2.Request('%s/upload.json'%self.base)
        req.add_header('Content-Type', 'application/json')
        response = urllib2.urlopen(req, json.dumps(data), context=context)
        print "network synced"
        
        res = self.application.getAllProbes()
        data = {
          'ap':[],
          'probes': res,
          'stations': []
        }
        req = urllib2.Request('%s/upload.json'%self.base)
        req.add_header('Content-Type', 'application/json')
        response = urllib2.urlopen(req, json.dumps(data), context=context)
        print "probes synced"
        
        res = self.application.getAllStations('date > "%s"'%date)
        data = {
          'ap':[],
          'probes': [],
          'stations': res
        }
        req = urllib2.Request('%s/upload.json'%self.base)
        req.add_header('Content-Type', 'application/json')
        response = urllib2.urlopen(req, json.dumps(data), context=context)
        
        print "stations synced"
      except:
        print "Sync unavailable"
      time.sleep(60)

  def stop(self):
      self.running = False
      
class WebuiHTTPHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
      pass
    
    def _parse_url(self):
        # parse URL
        path = self.path.strip('/')
        sp = path.split('?')
        if len(sp) == 2:
            path, params = sp
        else:
            path, = sp
            params = None
        args = path.split('/')

        return path,params,args
    
    def _get_status(self):
      gps_status = self.server.app.has_fix(True)
      wifi_status = self.server.app.wifiPosition is not None
      status = {
      'wifi': {'updated':self.server.app.last_updated},
      'position': {
        'gps':{
          'fix':(gps_status)
          },
        'wifi':{
          'fix':(wifi_status)
          }
        }
      }
      
      status["stat"] = self.server.app.getStats()
      status["current"] = self.server.app.getCurrent()
      
      if gps_status:
          status['position']['gps']['latitude'] = self.server.app.session.fix.latitude
          status['position']['gps']['longitude'] = self.server.app.session.fix.longitude
          status['position']['gps']['accuracy'] = self.server.app.gpspoller.getPrecision()
      
      status['sync'] = self.server.app.getLastUpdate()
      
      wifiPos = self.server.app.wifiPosition
      if wifiPos is not None:
        status['position']['wifi']['latitude'] = wifiPos[0]
        status['position']['wifi']['longitude'] = wifiPos[1]
        status['position']['wifi']['accuracy'] = wifiPos[2]
      
      self.send_response(200)
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      # push data
      self.wfile.write(json.dumps(status))
    
    def _get_file(self, path):
      _path = os.path.join(self.server.www_directory,path)
      if os.path.exists(_path):
          try:
          # open asked file
              data = open(_path,'r').read()

              # send HTTP OK
              self.send_response(200)
              self.end_headers()

              # push data
              self.wfile.write(data)
          except IOError as e:
                self.send_500(str(e))
      
    def _get_kml(self):
      try:
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        import simplekml
        kml = simplekml.Kml()
        networks = self.server.app.getAll()
        
        for n in networks["networks"]:
          lat = n[5]
          lon = n[4]
          name = n[1]
          kml.newpoint(name=name, coords=[(lon,lat)])
          kml_str = unicode(kml.kml()).encode('utf8')
        self.wfile.write(kml_str)
      except:
        self.send_response(500)
    
    def _get_wifis(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      networks = self.server.app.getAll()
      data = []
      for n in networks["networks"]:
        d = {}
        d["latitude"] = n[5]
        d["longitude"] = n[4]
        d["essid"] = n[1]
        d["bssid"] = n[0]
        d["encryption"] = n[2]
        data.append(d)
      
      self.wfile.write(json.dumps(data))
    
    def _get_stations(self, search = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      data = self.server.app.getAllStations(search)
      self.wfile.write(json.dumps(data))
    
    def _get_bt_stations(self, search = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      data = self.server.app.getAllBtStations(search)
      self.wfile.write(json.dumps(data))
    
    def _get_probes(self, essid = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      if essid is not None:
        data = self.server.app.getAllProbes(False, essid)
      else:
        probes = self.server.app.getAllProbes(True)
        data = []
        for n in probes:
          s = {}
          s["essid"] = n[0]
          s["count"] = n[1]
          s["ap"] = n[2]
          data.append(s)
      
      self.wfile.write(json.dumps(data))
    
    def _get_csv(self):
      #try:
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      networks = self.server.app.getAll()
      csv="SSID;BSSID;ENCRYPTION;LATITUDE;LONGITUDE;\r\n"
      for n in networks["networks"]:
        lat = n[5]
        lon = n[4]
        ssid = n[1]
        bssid = n[0]
        encryption = n[2]
        csv += '"%s"; "%s"; "%s"; %s; %s\r\n'%(ssid, bssid, encryption, lat, lon)
      csv = unicode(csv).encode('utf8')
      self.wfile.write(csv)
      #except:
        #self.send_response(500)
    
    def _get_stats(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      stats = self.server.app.getStats(True)
      self.wfile.write(json.dumps(stats))
    
    def setParam(self, key,value):
      if key == 'minAccuracy':
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.server.app.args.accuracy = float(value)
        self.wfile.write(json.dumps('ok'))
    
    def do_POST(self):
        path,params,args = self._parse_url()
        if ('..' in args) or ('.' in args):
            self.send_400()
            return
        if len(args) == 1 and args[0] == 'upload.json':
          if(not self.server.app.args.enable):
            self.send_response(403)
            return
          self.send_response(200)
          self.send_header('Content-type','text/html')
          self.end_headers()
          length = int(self.headers['Content-Length'])
          post = self.rfile.read(length)
          post = post.decode('string-escape').strip('"')
          data = json.loads(post,strict=False)
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
            self.server.app.update(network)
          
          for bssid in data['stations']:
            for n in data['stations'][bssid]["points"]:
              station = {}
              station['id'] = n[0]
              station['bssid'] = n[1]
              station['latitude'] = n[2]
              station['longitude'] = n[3]
              station['signal'] = n[4]
              station['date'] = n[5]
              self.server.app.update_station(station)
          
          for probe in data['probes']:
            p = {}
            p['bssid'] = probe[0]
            p['essid'] = probe[1]
            self.server.app.update_probe(p)
          
          self.wfile.write(json.dumps('ok'))
    
    def _get_manufacturer(self, manufacturer):
      basepath = os.path.join('img','manufacturer')
      path = os.path.join(basepath,"%s.png"%manufacturer)
      fullpath = os.path.join(self.server.www_directory,path)
      if os.path.exists(fullpath):
        return self._get_file(path)
      else:
        return self._get_file(os.path.join(basepath,"unknown.png"))
    
    def do_GET(self):
        path,params,args = self._parse_url()
        if ('..' in args) or ('.' in args):
            self.send_400()
            return
        if len(args) == 1 and args[0] == '':
            path = 'index.html'
        if len(args) == 1 and args[0] == 'status.json':
            return self._get_status()
        elif len(args) == 1 and args[0] == 'set':
          key = params.split('=')[0]
          value = params.split('=')[1]
          return self.setParam(key,value)
        elif len(args) == 1 and args[0] == 'kml':
            return self._get_kml()
        elif len(args) == 1 and args[0] == 'manufacturer':
            return self._get_manufacturer(params.split('=')[1])
        elif len(args) == 1 and args[0] == 'csv':
            return self._get_csv()
        elif len(args) == 1 and args[0] == 'wifis.json':
            return self._get_wifis()
        elif len(args) == 1 and args[0] == 'stations.json':
            if params is not None:
              params = params.split('search=')[1]
            return self._get_stations(params)
        elif len(args) == 1 and args[0] == 'bt_stations.json':
            if params is not None:
              params = params.split('search=')[1]
            return self._get_bt_stations(params)
        elif len(args) == 1 and args[0] == 'probes.json':
          if params is not None:
              params = params.split('essid=')[1]
          return self._get_probes(params)
        elif len(args) == 1 and args[0] == 'stats.json':
            return self._get_stats()
        else:
            return self._get_file(path)
      
class WebuiHTTPServer(ThreadingMixIn, HTTPServer, Thread):
  def __init__(self, server_address, app, RequestHandlerClass, bind_and_activate=True):
    HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
    threading.Thread.__init__(self)
    self.app = app
    self.www_directory = "www/"
    self.stopped = False
    
  def stop(self):
    self.stopped = True
    
  def run(self):
      while not self.stopped:
          self.handle_request()
      
class Application (threading.Thread):
    def __init__(self, args):
        threading.Thread.__init__(self)
        self.args = args
        self.manufacturers_db = '/usr/share/wireshark/manuf'
        self.manufacturers = {}
        self.lock = Lock()
        self.stopped = False
        self.session = gps(mode=WATCH_ENABLE)
        self.ignore_bssid = []
        self.last_updated = 0
        self.network_count = 0
        self.interface = ''
        self.airodump = None
        self.wifiPosition = None
        self.bluePoller = BluetoothPoller(self)
        
        if(self.args.accuracy is None):
          self.args.accuracy = min_gpsd_accuracy
        
        if(self.args.database is not None):
            db = self.args.database
        else:
            db = "./wifimap.db"
        self.db = sqlite3.connect(db, check_same_thread=False)
        self.query_db = self.db.cursor()
        
        try:
            self.query('''select * from wifis''')
        except:
            self.createDatabase()
        
        self.gpspoller = GpsPoller(self.session, self)
        
        self.gpspoller.start()
        self.bluePoller.start()
        
        for b in self.getConfig('bssid').split(','):
          self.ignore_bssid.append(b)
        
        if args.bssid is not None:
          for b in args.bssid:
            self.ignore_bssid.append(b)
        
        if not args.enable:
          args.enable = self.getConfig('enable') == 'true'
        
        if args.synchro is None:
          if self.getConfig('synchro') != '':
            args.synchro = self.getConfig('synchro')
        
        if args.synchro is not None:
          self.synchronizer = Synchronizer(self, args.synchro)
          self.synchronizer.start()
        
        try:
          if self.args.interface is not None:
              self.interface = self.args.interface
          else:
              self.interface = self.getWirelessInterfacesList()[0]
          self.ignore_bssid.append(self.getMacFromIface(self.interface))
        except:
          self.log("App", "No wifi interface")
        
        if self.args.monitor:
          if self.interface != 'mon0':
            if 'mon0' not in self.getWirelessInterfacesList():
              cmd = ['airmon-ng', 'start' ,self.interface]
              p = subprocess.Popen(cmd)
              p.wait()
          self.interface = 'mon0'
                
        
        print self.getConfig('www')
        if self.args.www is not None:
            port = int(self.args.www)
        else:
          if self.getConfig('www') != '':
            port = int(self.getConfig('www'))
          else:
            port = 8686
            
        self.loadManufacturers()
        try:
          self.httpd = WebuiHTTPServer(("", port),self, WebuiHTTPHandler)
          self.httpd.start()
        except:
          self.log("http", "web hmi not available")
    
    def query(self, query):
      with self.lock:
        self.query_db.execute(query)
    
    def fetchone(self, query):
      with self.lock:
        self.query_db.execute(query)
        return self.query_db.fetchone()
    
    def fetchall(self, query):
      with self.lock:
        self.query_db.execute(query)
        return self.query_db.fetchall()
    
    def getConfig(self, _key):
      try:
        q = '''select value from config where key == "%s"'''%_key
        res = self.query.fetchone(q)
        return res[0]
      except:
        return ''
    
    def packet_handler(self, pkt):
      if pkt.haslayer(Dot11):
        if pkt.type == 0 and pkt.subtype == 8:
          rssi =0
          print "==> %s %s %s"%(rssi, pkt.addr2, pkt.info)
          pkt.show()
    
    def getStats(self, full = False):
      stat = {'wifis': {}, 'stations':{}, 'bt_stations':{}, 'probes':{}}
      q = '''select count(*) from wifis where encryption == 0'''
      try:
        stat['wifis']['open'] = self.fetchone(q)[0]
      except:
        stat['wifis']['open'] = 0
      
      q = '''select count(*) from wifis'''
      stat['wifis']['all'] = self.fetchone(q)[0]
      
      if full:
        q = '''select essid, count(*) as count_essid from wifis group by essid order by count_essid desc limit 20'''
        stat['wifis']['top'] = self.fetchall(q)
        
        q = '''select count(*) as count_manuf, substr(bssid,0,9) as manufacturer from wifis group by manufacturer order by count_manuf desc limit 20'''
        stat['wifis']['manufacturer'] = []
        for m in self.fetchall(q):
          stat['wifis']['manufacturer'].append({
            'count':  m[0],
            'manufacturer': self.getManufacturer(m[1])
            })
        
        q = '''select essid, count(*) as count_essid from probes group by essid order by count_essid desc limit 20'''
        stat['probes']['top'] = self.fetchall(q)
        
        q = '''select count(distinct bssid) from stations'''
        stat['stations']['all'] = self.fetchone(q)[0]
        
        q = '''select count(distinct bssid) from bt_stations'''
        stat['bt_stations']['all'] = self.fetchone(q)[0]
      
      q = '''select count(distinct essid) from probes'''
      stat['probes']['all'] = self.fetchone(q)[0]
      return stat
    
    def getLastUpdate(self):
        q = '''select date from wifis order by date desc limit 1'''
        return self.fetchone(q)
    
    def getWifisFromEssid(self, essid):
      where = ''
      if isinstance(essid, str):
        where = 'essid="%s"'%essid 
      else:
        where = 'essid in ("%s")'%','.join(essid)
      
      q='select * from wifis where %s'%where
      return self.fetchall(q)
      
    
    def getStationsPerDay(self, limit = 0):
      limit_str = ''
      if limit_str != 0:
        limit_str = 'LIMIT %s'%limit
      q='''select bssid, date(date), count(distinct date(date)) from stations group by bssid order by count(distinct date(date)) DESC, date %s'''%limit
      return self.fetchall(q)
    
    def getAllStations(self, search = None):
      stations = []
      search_where = ""
      if search is not None:
        search_where = "where %s"%search
      
      q = 'select * from stations %s'%search_where
      res = self.fetchall(q)
      if res is not None:
        for s in res:
          station = {}
          station['bssid'] = s[1]
          station['latitude'] = s[2]
          station['longitude'] = s[3]
          station['signal'] = s[4]
          station['date'] = s[5]
          station['manufacturer'] = self.getManufacturer(station['bssid'])
          stations.append(station)
        
      return stations
    
    def getAllBtStations(self, search):
      stations = []
      search_where = ""
      if search is not None:
        search_where = "where %s"%search
      
      q = 'select * from bt_stations %s'%search_where
      res = self.fetchall(q)
      if res is not None:
        for s in res:
          station = {}
          station['bssid'] = s[1]
          station['class'] = s[2]
          station['name'] = s[3]
          station['latitude'] = s[4]
          station['longitude'] = s[5]
          station['date'] = s[6]
          station['manufacturer'] = self.getManufacturer(station['bssid'])
          stations.append(station)
        
      return stations
    
    def getAllProbes(self, distinct = False, essid = None):
      probes = {}
      essid_where = ""
      if essid is not None:
        essid_where = 'where essid = "%s"'%essid
      if not distinct:
        q = 'select * from probes %s order by essid'%essid_where
      else:
        q = 'select P.essid, count(*) as probes_count, (select count(*) from wifis W where W.essid = P.essid) as wifis_count from probes P %s group by P.essid order by probes_count desc, wifis_count desc'%essid_where
      return self.fetchall(q)
      return probes
    
    def getAll(self, date = None):
        wifis = {}
        date_where = ''
        if date is not None:
          date_where = 'where date > "%s"'%date
        q = 'select * from wifis %s order by latitude, longitude'%date_where
        wifis["networks"] = self.fetchall(q)
        
        q = 'select avg(latitude), avg(longitude) from wifis %s group by date order by date desc limit 1'%date_where
        wifis["center"] = self.fetchone(q)
        wifis["stat"] = self.getStats()
        return wifis
    
    def getLast(self):
        wifis = {}
        q = '''select * from wifis order by date desc, latitude, longitude limit 10'''
        wifis["networks"] = self.fetchall(q)
        wifis["stat"] = self.getStats()
        return wifis
    
    def getCurrent(self):
      wifis = self.scanForWifiNetworks()
      probes = []
      stations = []
      
      if self.args.monitor and not USE_SCAPY:
        probes = self.airodump.probes
        stations = self.airodump.stations
      data = {}
      data['wifis'] = wifis
      data['probes'] = probes
      data['stations'] = stations
      data['bluetooth'] = self.bluePoller.stations
      return data
    
    def createDatabase(self):
        print "initiallize db"
        self.query('''CREATE TABLE wifis
            (bssid text, essid text, encryption bool, signal real, longitude real, latitude real, frequency real, channel int, mode text, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, gps boolean)''')
        self.query('''CREATE TABLE config
            (key text, value text)''')
        self.query('''CREATE TABLE gps
            (latitude real, longitude real, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.query('''CREATE TABLE stations
            (id integer primary key, bssid  text, latitude real, longitude real, signal real, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.query('''CREATE TABLE bt_stations
            (id integer primary key, bssid  text, class integer, name text, latitude real, longitude real, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.query('''CREATE TABLE probes (bssid  text, essid text)''')
    
    def log(self, name, value):
        print "%s   %s : %s"%(datetime.datetime.now(), name, value)
    
    def stop(self):
        self.stopped = True
        self.gpspoller.stop()
        self.gpspoller.join()
        self.synchronizer.stop()
        self.synchronizer.join()
        self.httpd.stop()
        self.httpd.join()
        self.airodump.stop()
        self.airodump.join()
    
    def has_fix(self, accurate = True):
      return self.gpspoller.has_fix(accurate)
    
    def run(self):
        if self.interface == '':
          self.log("wifi", "no interface")
          while not self.stopped:
            time.sleep(1)
          return
        if self.args.monitor:
          if USE_SCAPY:
            sniff(iface=self.interface, prn = self.packet_handler)
          else:
            self.airodump = AirodumpPoller(self)
            self.airodump.start()
        
        while not self.stopped:
          try:
            wifis = self.scanForWifiNetworks()
            updated = 0
            for w in wifis:
              try:
                if self.update(w):
                    updated += 1
              except:
                self.log("wifi", "insert fails")
                print w
                
            if updated != 0:
                self.log("updated wifi", updated)
            self.last_updated = updated
            self.network_count = len(wifis)
            self.wifiPosition = self.getWifiPosition(wifis)
            
            if self.args.monitor and not USE_SCAPY:
              try:
                updated = 0
                for p in self.airodump.probes:
                  if self.update_probe(p):
                    updated += 1
                  if updated != 0:
                    self.log("updated probes", updated)
              except:
                self.log("wifi", "probes insert fails")
              
              try:
                updated = 0
                for s in self.airodump.stations:
                  if self.update_station(s):
                    updated += 1
                
                if updated != 0:
                    self.log("updated stations", updated)
              except:
                self.log("wifi", "stations insert fails")
            
            bt = self.bluePoller.stations
            updated = 0
            for b in bt:
              try:
                if self.update_bt_station(b):
                    updated += 1
              except:
                self.log("bluetooth", "insert fails")
                print b
                
            if updated != 0:
                self.log("updated bluetooth", updated)
            
            with self.lock:
              self.db.commit()
          except Exception as e:
            self.log("wifi", 'fail')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
          if self.args.sleep is not None:
              sleep = int(self.args.sleep)
          else:
              sleep = 1
          time.sleep(sleep)
      
      
    def update_bt_station(self, station):
      if not station.has_key('latitude'):
        return False
      q = '''select * from bt_stations where bssid="%s" and latitude="%s" and longitude="%s"'''%(station["bssid"], station["latitude"], station["longitude"])
      res = self.fetchone(q)
      if res is None:
        q = '''insert into bt_stations (id, bssid, class, name, latitude, longitude) values (NULL, "%s", "%s", "%s", "%s", "%s")'''%(station["bssid"], station['class'], station['name'], station["latitude"], station["longitude"])
        self.query(q)
        return True
      return False
    
    def update(self, wifi):
        if not wifi.has_key('latitude'):
          return False
        if math.isnan(wifi["longitude"]):
            return False
                
        q = '''select * from wifis where bssid="%s" and essid="%s"'''%(wifi["bssid"], wifi["essid"])
        res = self.fetchone(q)
        if res is None:
            gps = 0
            if wifi["gps"]:
              gps = 1
            q = 'insert into wifis (bssid, essid, encryption, signal, longitude, latitude, frequency, channel, mode, date, gps) values ("%s", "%s", %s, %s, %s, %s, %s, %s, "%s", CURRENT_TIMESTAMP, %s)'%(wifi["bssid"], wifi["essid"], int(wifi["encryption"]), wifi["signal"], wifi["longitude"], wifi["latitude"], wifi["frequency"], wifi["channel"], wifi["mode"], gps)
            try:
              self.query(q)
              return True
            except:
              print "sqlError: %s"%q
              return False
        else:
            try:
              signal = res[3]
              gps = res[10]
              where_source = ""
              gps = 1
              if not gps:
                gps = 0
                where_source = ' and gps = 0 ' 
              q = 'update wifis set bssid="%s", essid="%s", encryption=%s, signal=%s, longitude=%s, latitude=%s, frequency=%s, channel=%s, mode="%s", gps="%s", date=CURRENT_TIMESTAMP where bssid="%s" and essid="%s" %s'%(wifi["bssid"], wifi["essid"], int(wifi["encryption"]), wifi["signal"], wifi["longitude"], wifi["latitude"], wifi["frequency"], wifi["channel"], wifi["mode"], gps, wifi["bssid"], wifi["essid"], where_source)
              if wifi["signal"] < signal:
                  self.query(q)
                  return True
            except:
              print "sqlError: %s"%q
        return False
    
    def update_probe(self, probe):
      q = '''select * from probes where bssid="%s" and essid="%s"'''%(probe["bssid"], probe["essid"])
      res = self.fetchone(q)
      if res is None:
        q = '''insert into probes (bssid, essid) values ("%s", "%s")'''%(probe["bssid"], probe["essid"])
        self.query(q)
        return True
      return False

    def update_station(self, station):
      if not station.has_key('latitude'):
        return False
      q = '''select * from stations where bssid="%s" and latitude="%s" and longitude="%s"'''%(station["bssid"], station["latitude"], station["longitude"])
      res = self.fetchone(q)
      if res is None:
        q = '''insert into stations (id, bssid, latitude, longitude, signal) values (NULL, "%s", "%s", "%s", "%s")'''%(station["bssid"], station["latitude"], station["longitude"], station["signal"])
        self.query(q)
        self.log("station", "update")
        return True
      return False
    
    def loadManufacturers(self):
      try:
        manuf = open(self.manufacturers_db,'r').read()
        res = re.findall("(..:..:..)\s(.*)\s#\s(.*)", manuf)
        if res is not None:
          for m in res:
            self.manufacturers[m[0]] = m[1].strip()
      except:
        pass
      return ''
    
    
    def getManufacturer(self,_bssid):
      try:
        # keep only 3 first bytes
        signature = ':'.join(_bssid.split(":")[:3])
        return self.manufacturers[signature.upper()]
      except:
        pass
      return ''
    
    def scanForWifiNetworks(self):
        if self.args.monitor:
          return self.airodump.getNetworks()
        else:
          networkInterface = self.interface
          output = ""
          if(networkInterface!=None):		
              command = ["iwlist", networkInterface, "scanning"]
              process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
              process.wait()
              (stdoutdata, stderrdata) = process.communicate();
              output =  stdoutdata
              return self.parseIwlistOutput(output)
    
    def parseIwlistOutput(self, data):
        networks = {}
        res = re.findall("Address: (.*)", data)
        if res is not None:
            networks["bssid"] = res
        
        res = re.findall("ESSID:\"(.*)\"", data)
        if res is not None:
            networks["essid"] = res
    
        res = re.findall("Mode:(.*)", data)
        if res is not None:
            networks["mode"] = res
            
        res = re.findall("Channel:(\d*)", data)
        if res is not None:
            networks["channel"] = res
            
        res = re.findall("Frequency:(.*) GHz", data)
        if res is not None:
            networks["frequency"] = res
    
        res = re.findall("Signal level=(.*) dBm", data)
        if res is not None:
            networks["signal"] = res
        
        res = re.findall("Encryption key:(.*)", data)
        if res is not None:
            networks["encryption"] = res
            
        pos = self.getPosition()
        fix = pos is not None
        if fix:
          lon, lat, source = pos
        wifis = []
        
        for i in range(0,len(networks["essid"])):
            n = {}
            if fix:
              n["latitude"] = lat
              n["longitude"] = lon
              n['gps'] = source == 'gps'
            n["bssid"] = networks["bssid"][i]
            n["essid"] = networks["essid"][i]
            n["mode"] = networks["mode"][i]
            n["channel"] = networks["channel"][i]
            n["frequency"] = float(networks["frequency"][i])
            n["signal"] = float(networks["signal"][i])
            n["encryption"] = networks["encryption"][i] == "on"
            if n["bssid"] not in self.ignore_bssid:
                wifis.append(n)
        return wifis
        
            
    def getWifiPosition(self, wifis):
      bssid = []
      if len(wifis) < 3:
        return None
      for n in wifis:
        bssid.append("\"%s\""%n["bssid"])
      q = "select avg(latitude), avg(longitude), max(latitude)-min(latitude), max(longitude)-min(longitude) from wifis where bssid in ( %s )"%(','.join(bssid))
      res = self.fetchone(q)
      if res is not None:
        if res[0] is None:
          return None
        return (res[0], res[1], self.haversine(0,0,res[2],res[3]))
           
    def getPosition(self):
      if self.gpspoller.has_fix():
        longitude = self.session.fix.longitude
        latitude = self.session.fix.latitude
        return (longitude, latitude, 'gps')
      elif self.wifiPosition is not None:
        return (self.wifiPosition[1], self.wifiPosition[0], 'wifi')
      return None
            
    def getWirelessInterfacesList(self):
        networkInterfaces=[]		
        command = ["iwconfig"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        (stdoutdata, stderrdata) = process.communicate();
        output = stdoutdata
        lines = output.splitlines()
        for line in lines:
                if(line.find("IEEE 802.11")!=-1):
                        networkInterfaces.append(line.split()[0])
        return networkInterfaces
      
    def getMacFromIface(self, _iface):
      path = "/sys/class/net/%s/address"%_iface
      data = open(path,'r').read()
      data = data[0:-1] # remove EOL
      return data
    
    
    def haversine(self, lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 # Radius of earth in kilometers. Use 3956 for miles
        return c * r
    
    def is_mobile(self, manufacturer):
      return manufacturer in ['Apple', 'Nokia', 'Google', "4pMobile", "AavaMobi", "Advanced", "Asmobile", "AutonetM", "AzteqMob", "BejingDa", "Cambridg", "CasioHit", "Cellebri", "CgMobile", "ChinaMob", "CnfMobil", "CustosMo", "DatangMo", "DeltaMob", "DigitMob", "DmobileS", "EzzeMobi", "Farmobil", "Far-Sigh", "FuturaMo", "GmcGuard", "Guangdon", "HisenseM", "HostMobi", "IgiMobil", "IndigoMo", "InqMobil", "Ipmobile", "JdmMobil", "Jetmobil", "JustInMo", "KbtMobil", "L-3Commu", "LenovoMo", "LetvMobi", "LgElectr", "LiteonMo", "MemoboxS", "Microsof", "Mobacon", "Mobiis", "Mobilarm", "Mobileac", "MobileAc", "MobileAp", "Mobilear", "Mobileco", "MobileCo", "MobileCr", "MobileDe", "Mobileec", "MobileIn", "MobileMa", "MobileSa", "Mobileso", "MobileTe", "MobileXp", "Mobileye", "Mobilico", "Mobiline", "Mobilink", "Mobilism", "Mobillia", "Mobilmax", "Mobiltex", "Mobinnov", "Mobisolu", "Mobitec", "Mobitek", "MobiusTe", "Mobiwave", "Moblic", "Mobotix", "Mobytel", "Motorola", "NanjingS", "NecCasio", "P2Mobile", "Panasoni", "PandoraM", "Pointmob", "PoshMobi", "Radiomob", "RadioMob", "RapidMob", "RttMobil", "Shanghai", "Shenzhen", "SianoMob", "Smobile", "SonyEric", "SonyMobi", "Sysmocom", "T&AMobil", "TcmMobil", "TctMobil", "Tecmobil", "TinnoMob", "Ubi&Mobi", "Viewsoni", "Vitelcom", "VivoMobi", "XcuteMob", "XiamenMe", "YuduanMo"]

def main(args):
    f = open("/var/run/wifimap", 'w')
    f.write('%s'%os.getpid())
    f.close()
    app = Application(args)
    app.start()
    try:
        while True:
          time.sleep(1)
    except KeyboardInterrupt:
        print "Exiting..."
        app.stop()
    print "stopped"
        


main(parse_args())
