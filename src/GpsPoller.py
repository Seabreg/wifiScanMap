import threading
from gps import *
import os
try:
  import RPi.GPIO as GPIO
  GPIO.setmode(GPIO.BCM) 
except:
  print "No gpio"


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
