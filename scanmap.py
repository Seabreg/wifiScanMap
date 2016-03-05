#!/usr/bin/env python

import subprocess
import threading
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
    
    def do_GET(self):
        path,params,args = self._parse_url()
        if ('..' in args) or ('.' in args):
            self.send_400()
            return
        if len(args) == 1 and args[0] == '':
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
                    names = "%s<li>%s %s</li>"%(names,key, i[1])
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
        elif len(args) == 1 and args[0] == 'status.json':
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
        else:
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
        self.stopped = False
        self.networks = []
        self.session = gps(mode=WATCH_ENABLE)
        self.gpspoller = GpsPoller(self.session)
        self.gpspoller.start()
        self.last_fix = False
        self.last_updated = 0
        if self.args.interface is not None:
            self.interface = self.args.interface
        else:
            self.interface = self.getWirelessInterfacesList()[0]

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
        self.httpd = WebuiHTTPServer(("", port),self, WebuiHTTPHandler)
        self.httpd.start()
    def getAll(self):
        wifis = {}
        self.query.execute('''select * from wifis''')
        wifis["networks"] = self.query.fetchall()
        
        self.query.execute('''select avg(latitude), avg(longitude) from wifis group by date order by date desc limit 1''')
        wifis["center"] = self.query.fetchone()
        return wifis
    
    def createDatabase(self):
        print "initiallize db"
        self.query.execute('''CREATE TABLE wifis
             (bssid text, essid text, encryption bool, signal real, longitude real, latitude real, frequency real, channel int, mode text, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.query.execute('''CREATE TABLE logs
             (date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, name text, value text)''')
    
    def log(self, name, value):
        print "%s   %s : %s"%(datetime.datetime.now(), name, value)
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
            if len(wifis) == 0:
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
                  self.query.execute(q)
                  return True
            except:
              print "sqlError: %s"%q
        return False
    
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

def main(args):
    app = Application(args)
    try:
        app.run()
    except KeyboardInterrupt:
        print "Exiting..."
        app.stop()
        


main(parse_args())
