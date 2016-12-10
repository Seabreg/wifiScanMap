from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import json
from threading import Thread
import threading
import os
import PrctlTool
import re
import urllib

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
      wifiPos = self.server.app.wifiPosition
      wifi_status = wifiPos is not None
      status = {
      'wifi': {'updated':self.server.app.updates_count},
      'version': self.server.app.version,
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
      status['esp8266'] = self.server.app.synchronizer.get_esp8266_data()
      
      if gps_status:
          status['position']['gps']['latitude'] = self.server.app.session.fix.latitude
          status['position']['gps']['longitude'] = self.server.app.session.fix.longitude
          status['position']['gps']['accuracy'] = self.server.app.gpspoller.getPrecision()
      
      if wifiPos is not None:
        status['position']['wifi']['latitude'] = wifiPos[0]
        status['position']['wifi']['longitude'] = wifiPos[1]
        status['position']['wifi']['accuracy'] = wifiPos[2]
      
      self.send_response(200)
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      # push data
      data = json.dumps(status, ensure_ascii=False)
      try:
        self.wfile.write(data.encode('latin-1'))
      except Exception as e:
        print e
        print data
    
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
    
    def _get_wifis(self, p0 = None, p1 = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      networks = self.server.app.getAll(p0, p1)
      data = []
      for n in networks["networks"]:
        d = {}
        d["latitude"] = n[5]
        d["longitude"] = n[4]
        d["essid"] = n[1]
        d["bssid"] = n[0]
        d["encryption"] = n[2]
        data.append(d)
      
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
    def _get_stations(self, search = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      data = self.server.app.getAllStations(search)
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
    def _get_devices(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      data = self.server.app.getDevices()
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
    def _get_bt_stations(self, search = None):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      data = self.server.app.getAllBtStations(search)
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
    def _get_probes(self, essid = None):
      self.send_response(200)
      self.send_header('Content-type','application/json; charset=utf-8')
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
      
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
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
      self.wfile.write(json.dumps(stats, ensure_ascii=False))
    
    def setParam(self, key,value):
      if key == 'minAccuracy':
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.server.app.args.accuracy = float(value)
        self.wfile.write(json.dumps('ok', ensure_ascii=False))
    
    def _post_upload(self, post):
      if(not self.server.app.args.enable):
        self.send_response(403)
        return
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()

      data = json.loads(post,strict=False)
      self.server.app.synchronizer.synchronize_data(data)
      self.wfile.write(json.dumps('ok', ensure_ascii=False))
     
    def _post_esp8266(self, post):
      if(not self.server.app.args.enable):
        self.send_response(403)
        return
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      
      data = json.loads(post,strict=False)
      self.server.app.synchronizer.synchronize_esp8266(data)

    def _post_users_dns(self, post):
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      
      data = json.loads(post,strict=False)
      self.server.app.update_dns(data)

    def do_POST(self):
        path,params,args = self._parse_url()
        if ('..' in args) or ('.' in args):
            self.send_400()
            return
        try:
          length = int(self.headers['Content-Length'])
          post = self.rfile.read(length)
          post = post.decode('string-escape').strip('"')
          if len(args) == 1 and args[0] == 'upload.json':
            return self._post_upload(post)
          
          if len(args) == 1 and args[0] == 'esp8266.json':
            return self._post_esp8266(post)
          if len(args) == 1 and args[0] == 'users.json':
            return self._post_users_dns(post)
        except Exception as e:
          print e
          f = open('/tmp/sync_esp8266.json','w')
          f.write(post)
          f.close()
    
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
      self.wfile.write(json.dumps(station, ensure_ascii=False))
    
    def _get_synchronize(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      sync = self.server.app.synchronizer.synchronize()
      self.wfile.write(json.dumps(sync, ensure_ascii=False))
    
    def _get_sync(self, hostname):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      sync = self.server.app.synchronizer.get_sync(hostname)
      self.wfile.write(json.dumps(sync, ensure_ascii=False))
      
    def _get_delete(self, bssid,essid):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      delete = self.server.app.delete(bssid,essid)
      self.wfile.write(json.dumps(delete, ensure_ascii=False))
    
    def _get_position(self):
      self.send_response(200)
      self.send_header('Content-type','application/json')
      self.send_header('Access-Control-Allow-Origin','*')
      self.end_headers()
      
      data = {}
      wifiPos = self.server.app.wifiPosition
      if wifiPos is not None:
        data['latitude'] = wifiPos[0]
        data['longitude'] = wifiPos[1]
        data['accuracy'] = wifiPos[2]
        data['used_wifis'] = wifiPos[3]
      
      self.wfile.write(json.dumps(data, ensure_ascii=False))
    
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
            p0 = None
            p1 = None
            if params is not None:
              m = re.match(
              r"lat=(.*)\&lon=(.*)\&lat1=(.*)\&lon1=(.*)",params)
            if m is not None:
              lat, lon, lat1, lon1 = m.groups()
              p0 = (lat,lon)
              p1 = (lat1,lon1)
            return self._get_wifis(p0, p1)
        elif len(args) == 1 and args[0] == 'synchronize.json':
            return self._get_synchronize()
        elif len(args) == 1 and args[0] == 'position.json':
            return self._get_position()
        elif len(args) == 1 and args[0] == 'stations.json':
            if params is not None:
              params = urllib.unquote(params.split('search=')[1])
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
        elif len(args) == 1 and args[0] == 'devices.json':
            return self._get_devices()
        elif len(args) == 1 and args[0] == 'sync.json':
          if params is not None:
              params = params.split('hostname=')[1]
          return self._get_sync(params)
        elif len(args) == 1 and args[0] == 'delete.json':
          if params is not None:
            m = re.match(
              r"bssid=(.*)\&essid=(.*)",params)
            if m is not None:
              bssid,essid = m.groups()
              essid = urllib.unquote(essid)
            else:
              bssid = params.split('bssid=')[1]
              essid = None
            return self._get_delete(bssid, essid)
        else:
            return self._get_file(path)
      
class WebuiHTTPServer(ThreadingMixIn, HTTPServer, Thread):
  allow_reuse_address = True
  
  def __init__(self, server_address, app, RequestHandlerClass, bind_and_activate=True):
    HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
    threading.Thread.__init__(self)
    self.app = app
    self.www_directory = "www/"
    self.stopped = False
    
  def stop(self):
    self.stopped = True
    
  def run(self):
      PrctlTool.set_title('webserver')
      while not self.stopped:
          self.handle_request()
