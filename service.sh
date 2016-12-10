#!/bin/bash

SCRIPT_PATH="${BASH_SOURCE[0]}";
cd `dirname $SCRIPT_PATH`

while true; do 
  python scanmap.py "$@" >>/tmp/wifimap.log 2>&1
  echo "============="
  date >> /tmp/wifimap.log
  kill -9 `cat /var/run/wifimap`
  kill -9 `cat /var/run/wifimap-airodump`
done
