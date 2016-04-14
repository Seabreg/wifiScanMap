#!/bin/bash
SCRIPT_PATH="${BASH_SOURCE[0]}";
cd `dirname $SCRIPT_PATH`
python scanmap.py $@ >/tmp/wifimap.log 2>&1
date >> /tmp/wifimap.log
