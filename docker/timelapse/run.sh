#!/bin/ash
httpd -h /data -p 80 &
python3 -u chelonest_timelapse.py
