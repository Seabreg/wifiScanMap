# WifiScanMap

Scan and map all 802.11 access point, stations probes and Bluetooth peripherals.

Initially inspired by https://github.com/cyberpython/WifiScanAndMap , this projects aims to play with common radio networks: Wi-Fi and Bluetooth.

Using tools such as iwlist, hcitool, or airmon-ng and a gpsd gps to logs data in an SQlite database, it provides a web HMI to monitor data processing and analyze already mapped data.

It was tested on recent Debian / Ubuntu and a flying Raspberry 1.
![Plane](doc/plane.png)


## Esp8266

An esp8266 version is available here [esp8266-wifiScanMap](https://github.com/mehdilauters/esp8266-wifiScanMap)

![WifiScanMap](https://github.com/mehdilauters/esp8266-wifiScanMap/raw/master/doc/blackbox_open.png)

## Results

You can find a quick analysis of a ~6 months collect reading [Results.md](Results.md)

## Installation

```shell
sudo apt install npm
npm install -g bower
bower install
sudo apt install gpsd aircrack-ng bluez
sudo python scanmap.py -m
xdg-open http://localhost:8686
```

## Features

- locate Wi-Fi access point and its metadata bssid, essid, signal and encryption
- locate itself thanks to already known access points
- if using airmon-ng (-m otpion)
  - record all probe request: bssid, essid
  - record all stations: bssid, signal, date and position
- if hcitool is installed
  - record all bluetooth stations: bssid, name, classe, date and position
- synchronize data to a remote server (running the same program, with -e option)

It was tested on a Raspberry Pi 1 with a Wi-Fi and a Bluetooth usb dongle.

## HMI

Angular / openlayers 3

### Main page

This page allow you to see your GPS and Wi-Fi computed position on a map, and all access point already mapped.
Clicking on point gives you additional informations (date, bssid, encryption, manufacturer...)
![Main Page wifis](doc/main.png)

You may also want to display all stations which crossed your way. Each point with the same color correspond to a unique bssid.

![Main Page stations](doc/main_stations.png)

### Offline page

This page allows you to see currents datas received (probes, stations, access points...) without map in order to be available withou internet connection
![Main Page stations](doc/offline.png)

### Probes page

On this page, you will see all probes request count and how many access point you know with this essid.
![Main Page stations](doc/probes.png)

Clicking on a probe will display all mac addresses which made the request.
![Main Page stations](doc/probes_list.png)

### Station page

This may be on of the more interesting one: given a station bssi, its location history will be displayed on the map, with all probed networks.
![Main Page stations](doc/station.png)
