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
import sqlite3
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from threading import Thread
import json

import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", help="wifi interface")    
    parser.add_argument("-s", "--sleep", help="wifi interface")  
    parser.add_argument("-d", "--database", help="wifi database")
    parser.add_argument('-w', '--www', help='www port')
    parser.add_argument('-b', '--bssid', help='ignore bssid', action='append', nargs='*')
    return parser.parse_args()


class GpsPoller(threading.Thread):
  def __init__(self, gpsd):
    threading.Thread.__init__(self)
    self.gpsd = gpsd
    self.current_value = None
    self.running = True #setting the thread running to true

  def run(self):
    while self.running:
      self.gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer

  def stop(self):
      self.running = False
    
    
class WebuiHTTPHandler(BaseHTTPRequestHandler):
        
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
    
    def _get_index(self):
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      networks = self.server.app.getAll()
      html = '''
      <script type="text/javascript" src="http://www.openlayers.org/api/OpenLayers.js"></script>
      <script type="text/javascript" src="http://www.openstreetmap.org/openlayers/OpenStreetMap.js"></script>
      <script src="https://code.jquery.com/jquery-1.11.2.min.js"></script>
      <script>
      var current_position;
      var markers;
          function update(){
          $.getJSON('/status.json').done( function(data){
              if(data['gps']['fix'])
              {
                  var lonLat = new OpenLayers.LonLat( data['gps']['position']['longitude'] ,data['gps']['position']['latitude']);
                  var newPx = map.getLayerPxFromLonLat(lonLat);
                  current_position.moveTo(newPx);
              }
              
          }) .fail(function(d, textStatus, error) {
      console.error("getJSON failed, status: " + textStatus + ", error: "+error)
});
          setTimeout(update,1000);
          }
      
          var map;
      
          var fromProjection = new OpenLayers.Projection("EPSG:4326");   // Transform from WGS 1984
          var toProjection   = new OpenLayers.Projection("EPSG:900913"); // to Spherical Mercator Projection
  
          function init(){
              map = new OpenLayers.Map('map',
                      { maxExtent: new OpenLayers.Bounds(-20037508.34,-20037508.34,20037508.34,20037508.34),
                      numZoomLevels: 18,
                      maxResolution: 156543.0399,
                      units: 'm'
                      });
              map.addLayer(new OpenLayers.Layer.OSM());
              
              markers = new OpenLayers.Layer.Markers( "Markers" );
              map.addLayer(markers);
              
              var lonLat = new OpenLayers.LonLat('''+str(networks['center'][1])+", "+str(networks['center'][0])+''').transform( fromProjection, toProjection);
              if (!map.getCenter()) map.setCenter (lonLat, 16);
              
              
              '''
      lastLat = None
      lastLon = None
      count = 0
      networks_same_position = []
      for n in networks["networks"]:
          lat = n[5]
          lon = n[4]
          name = n[1]
          if lastLat == None:
            lastLat = lat
            lastLon = lon
          if lat == lastLat and lon == lastLon:
            count += 1
            networks_same_position.append(n)
          else:
            names = '<ul>'
            open_icon=''
            for i in networks_same_position:
              key = ''
              if not i[2]:
                open_icon='-open'
              else:
                key = '<img src=\\"locked.png\\">'
              manufacturer = self.server.app.getManufacturer(i[0])
              names = "%s<li>%s %s %s</li>"%(names,key, i[1], manufacturer)
            name = "%s</ul>"%names
            icon = "marker%s.png"%open_icon
            if count >= 2:
              icon ="marker-few%s.png"%open_icon
            if count >= 4:
              icon ="marker-many%s.png"%open_icon
            html+= '''
          setMarker(markers, '''+str(lat)+''', '''+str(lon)+''', "'''+names+'''", "'''+icon+'''");'''
            networks_same_position = []
            networks_same_position.append(n)
            count = 1
            
          lastLat = lat
          lastLon = lon

      html +='''
              current_position = new OpenLayers.Marker(lonLat);
              feature = new OpenLayers.Feature.Vector(
                  new OpenLayers.Geometry.Point(0,0),
                  {}, {
                  fillColor : 'red',
                  fillOpacity : 0,                    
                  strokeColor : "#ffffff",
                  strokeOpacity : 1,
                  strokeWidth : 1,
                  pointRadius : 8
                  }
              );
          
              feature.style = {
              graphicWidth:48,
              rotation:0
              };
              current_position.feature = feature;
              markers.addMarker(current_position);

      
              setTimeout(update,1000);
          }
          
          function setMarker(markers, lat, lon, contentHTML, icon){
              var lonLatMarker = new OpenLayers.LonLat(lon, lat).transform( fromProjection, toProjection);
              var feature = new OpenLayers.Feature(markers, lonLatMarker);
              feature.closeBox = true;
              feature.popupClass = OpenLayers.Class(OpenLayers.Popup.FramedCloud, {minSize: new OpenLayers.Size(300, 180) } );
              feature.data.popupContentHTML = contentHTML;
              feature.data.overflow = "auto";
              
              if(icon != "")
              {
                  var icon = new OpenLayers.Icon(icon,new OpenLayers.Size(20, 50), new OpenLayers.Pixel(-10,-50));
                  var marker = new OpenLayers.Marker(lonLatMarker, icon);
                  marker.feature = feature;
              }

              if(contentHTML != "")
              {
                  var markerClick = function(evt) {
                          if (this.popup == null) {
                                  this.popup = this.createPopup(this.closeBox);
                                  map.addPopup(this.popup);
                                  this.popup.show();
                          } else {
                                  this.popup.toggle();
                          }
                          OpenLayers.Event.stop(evt);
                  };
                  marker.events.register("mousedown", feature, markerClick);
              }   

              markers.addMarker(marker);
      }
      </script>
      '''
      
      html += '''<body onload="init()">
      <div id="map"></map>
      </body>
      '''
      
      self.wfile.write(html)
    
    def _get_status(self):
      gps_status = self.server.app.getGPSData() != (0,0)
      
      status = {'gps':{
          'fix':(gps_status)
          },
      'wifi': {'updated':self.server.app.last_updated}
      }
      
      if gps_status:
          status['gps']['position'] = {'latitude':self.server.app.session.fix.latitude , 'longitude':self.server.app.session.fix.longitude}
      
      self.send_response(200)
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
    
    def _get_offline(self):
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      networks = self.server.app.getLast()
      
      html = '<html>'
      html += 'Current position: %s, %s <br/>'%(self.server.app.getGPSData()[0],self.server.app.getGPSData()[1])
      html += 'Current wifi scan: %s<br/>'%self.server.app.network_count
      html += 'Last update: %s<br/>'%self.server.app.last_updated
      
      html += '<hr/><ul>'
      for n in networks['networks']:
        name = n[1]
        date = n[9]
        key = ''
        if n[2]:
          key = '<img src="locked.png">'
        manufacturer = self.server.app.getManufacturer(n[0])
        if manufacturer != '':
          manufacturer = '%s<br/>'%manufacturer
        html += '<li>%s <b>%s</b> <br/>%s%s</li>'%(key, name, manufacturer, date)
        
      html += '</ul><hr/><h2>Stats</h2>'
      html += 'Total : %s<br/>'%networks['stat']['total']
      html += 'Total open : %s</br>'%networks['stat']['open_count']
      html += '<ul>'
      for n in networks['stat']['best']:
        html += '<li>%s : %s</li>'%(n[0],n[1])
      html += '</ul>'
      html += '</html>'
      self.wfile.write(html)
    
    def do_GET(self):
        path,params,args = self._parse_url()
        if ('..' in args) or ('.' in args):
            self.send_400()
            return
        if len(args) == 1 and args[0] == '':
            return self._get_index()
        elif len(args) == 1 and args[0] == 'status.json':
            return self._get_status()
        elif len(args) == 1 and args[0] == 'offline':
            return self._get_offline()
        else:
            return self._get_file(path)
      
class WebuiHTTPServer(ThreadingMixIn, HTTPServer, Thread):
  def __init__(self, server_address, app, RequestHandlerClass, bind_and_activate=True):
    HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
    threading.Thread.__init__(self)
    self.app = app
    self.www_directory = "www/"
    
  def run(self):
      while True:
          self.handle_request()
      
class Application:
    def __init__(self, args):
        self.args = args
        self.manufacturers_db = '/usr/share/wireshark/manuf'
        self.manufacturers = {}
        self.lock = Lock()
        self.stopped = False
        self.networks = []
        self.session = gps(mode=WATCH_ENABLE)
        self.gpspoller = GpsPoller(self.session)
        self.gpspoller.start()
        self.ignore_bssid = []
        if args.bssid is not None:
          for b in args.bssid:
            self.ignore_bssid.append(b)
        self.last_fix = False
        self.last_updated = 0
        self.network_count = 0
        if self.args.interface is not None:
            self.interface = self.args.interface
        else:
            self.interface = self.getWirelessInterfacesList()[0]
        self.ignore_bssid.append(self.getMacFromIface(self.interface))

        if(self.args.database is not None):
            db = self.args.database
        else:
            db = "./wifimap.db"
        self.db = sqlite3.connect(db, check_same_thread=False)
        self.query = self.db.cursor()
        try:
            self.query.execute('''select * from wifis''')
        except:
            self.createDatabase()
            
        if self.args.www is not None:
            port = int(self.args.www)
        else:
            port = 8686
            
        self.loadManufacturers()
        self.httpd = WebuiHTTPServer(("", port),self, WebuiHTTPHandler)
        self.httpd.start()
    
    def getStat(self):
      stat = {}
      with self.lock:
        self.query.execute('''select count(*) from wifis where encryption == 0''')
        stat['open_count'] = self.query.fetchone()[0]
        
        self.query.execute('''select count(*) from wifis''')
        stat['total'] = self.query.fetchone()[0]
        
        self.query.execute('''select essid, count(*) as nb from wifis group by essid order by nb desc limit 15''')
        stat['best'] = self.query.fetchall()
      return stat
    
    def getAll(self):
        wifis = {}
        with self.lock:
          self.query.execute('''select * from wifis order by latitude, longitude''')
          wifis["networks"] = self.query.fetchall()
          
          self.query.execute('''select avg(latitude), avg(longitude) from wifis group by date order by date desc limit 1''')
          wifis["center"] = self.query.fetchone()
        wifis["stat"] = self.getStat()
        return wifis
    
    def getLast(self):
        wifis = {}
        with self.lock:
          self.query.execute('''select * from wifis order by date desc, latitude, longitude limit 10''')
          wifis["networks"] = self.query.fetchall()
        wifis["stat"] = self.getStat()
        return wifis
    
    def createDatabase(self):
        print "initiallize db"
        with self.lock:
          self.query.execute('''CREATE TABLE wifis
              (bssid text, essid text, encryption bool, signal real, longitude real, latitude real, frequency real, channel int, mode text, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
          self.query.execute('''CREATE TABLE logs
              (date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, name text, value text)''')
    
    def log(self, name, value):
        print "%s   %s : %s"%(datetime.datetime.now(), name, value)
        with self.lock:
          q = 'insert into logs (name, value) values ("%s", "%s")'%(name, value)
          self.query.execute(q)
    
    def stop(self):
        self.stopped = True
        self.gpspoller.stop()
    
    def run(self):
        while not self.stopped:
            wifis = self.scanForWifiNetworks()
            updated = 0
            for w in wifis:
                if self.update(w):
                    updated += 1
            if updated != 0:
                self.log("updated", updated)
            self.last_updated = updated
            self.network_count = len(wifis)
            if self.network_count == 0:
                self.log("wifi", 'No results')
            self.db.commit()
            if self.args.sleep is not None:
                sleep = int(self.args.sleep)
            else:
                sleep = 1
            
            time.sleep(sleep)
    
    def update(self, wifi):
        if math.isnan(wifi["longitude"]):
            if self.last_fix:
                self.log("gps", 'NO_FIX')
                self.last_fix = False
            return False
        else:
            if not self.last_fix:
                self.log("gps", 'FIX')
                self.last_fix = True
                
        self.query.execute('''select * from wifis where bssid="%s" and essid="%s"'''%(wifi["bssid"], wifi["essid"]))
        res = self.query.fetchone()
        if res is None:
            q = 'insert into wifis (bssid, essid, encryption, signal, longitude, latitude, frequency, channel, mode, date) values ("%s", "%s", %s, %s, %s, %s, %s, %s, "%s", CURRENT_TIMESTAMP )'%(wifi["bssid"], wifi["essid"], int(wifi["encryption"]), wifi["signal"], wifi["longitude"], wifi["latitude"], wifi["frequency"], wifi["channel"], wifi["mode"])
            try:
              with self.lock:
                self.query.execute(q)
              return True
            except:
              print "sqlError: %s"%q
              return False
        else:
            try:
              signal = res[3]
              q = 'update wifis set bssid="%s", essid="%s", encryption=%s, signal=%s, longitude=%s, latitude=%s, frequency=%s, channel=%s, mode="%s", date=CURRENT_TIMESTAMP where bssid="%s" and essid="%s"'%(wifi["bssid"], wifi["essid"], int(wifi["encryption"]), wifi["signal"], wifi["longitude"], wifi["latitude"], wifi["frequency"], wifi["channel"], wifi["mode"], wifi["bssid"], wifi["essid"])
              if wifi["signal"] < signal:
                  with self.lock:
                    self.query.execute(q)
                  return True
            except:
              print "sqlError: %s"%q
        return False
    
    def loadManufacturers(self):
      try:
        manuf = open(self.manufacturers_db,'r').read()
        res = re.findall("(..:..:..)\s(.*)\s#\s(.*)", manuf)
        if res is not None:
          for m in res:
            self.manufacturers[m[0]] = m[1]
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
            
        lon, lat = self.getGPSData()
        wifis = []
        
        if lat !=0 and lon != 0:
            for i in range(0,len(networks["essid"])):
                n = {}
                n["latitude"] = lat
                n["longitude"] = lon
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
        
            
           
           
    def getGPSData(self):
        longitude = self.session.fix.longitude
        latitude = self.session.fix.latitude
        return (longitude, latitude)
            
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

def main(args):
    app = Application(args)
    try:
        app.run()
    except KeyboardInterrupt:
        print "Exiting..."
        app.stop()
        


main(parse_args())
