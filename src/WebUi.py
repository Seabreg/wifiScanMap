from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import json
from threading import Thread
import threading
import os

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
      'wifi': {'updated':self.server.app.updates_count},
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
      status["updates_count"] = self.server.app.updates_count
      status["current"] = self.server.app.getCurrent()
      
      if gps_status:
          status['position']['gps']['latitude'] = self.server.app.session.fix.latitude
          status['position']['gps']['longitude'] = self.server.app.session.fix.longitude
          status['position']['gps']['accuracy'] = self.server.app.gpspoller.getPrecision()
      
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
          hostname = data['hostname']
          
          
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
            self.server.app.update(network)
            self.server.app.synchronizer.update(hostname, 'ap', network['date'])
          
          for station in data['stations']:
            self.server.app.update_station(station)
            self.server.app.synchronizer.update(hostname, 'stations', station['date'])
          
          for probe in data['probes']:
            self.server.app.update_probe(probe)
            self.server.app.synchronizer.update(hostname, 'probes', '1980-01-01 00:00:00')
          
          self.wfile.write(json.dumps('ok'))
    
    def _get_manufacturer(self, manufacturer):
      basepath = os.path.join('img','manufacturer')
      path = os.path.join(basepath,"%s.png"%manufacturer)
      fullpath = os.path.join(self.server.www_directory,path)
      if os.path.exists(fullpath):
        return self._get_file(path)
      else:
        return self._get_file(os.path.join(basepath,"unknown.png"))
    
    def _get_station(self, bssid):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      station = self.server.app.getStation(bssid)
      self.wfile.write(json.dumps(station))
    
    def _get_synchronize(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      sync = self.server.app.synchronizer.synchronize()
      self.wfile.write(json.dumps(sync))
    
    def _get_sync(self, hostname):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      sync = self.server.app.get_sync(hostname)
      self.wfile.write(json.dumps(sync))
      
      
    
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
        elif len(args) == 1 and args[0] == 'synchronize.json':
            return self._get_synchronize()
        elif len(args) == 1 and args[0] == 'stations.json':
            if params is not None:
              params = params.split('search=')[1]
            return self._get_stations(params)
        elif len(args) == 1 and args[0] == 'bt_stations.json':
            if params is not None:
              params = params.split('search=')[1]
            return self._get_bt_stations(params)
        elif len(args) == 1 and args[0] == 'station.json':
            if params is not None:
              params = params.split('bssid=')[1]
            return self._get_station(params)
        elif len(args) == 1 and args[0] == 'probes.json':
          if params is not None:
              params = params.split('essid=')[1]
          return self._get_probes(params)
        elif len(args) == 1 and args[0] == 'stats.json':
            return self._get_stats()
        elif len(args) == 1 and args[0] == 'sync.json':
          if params is not None:
              params = params.split('hostname=')[1]
          return self._get_sync(params)
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