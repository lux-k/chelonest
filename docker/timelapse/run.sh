#!/bin/ash
httpd -h /data -p 80 &
pip install -r requirements.txt
python3 -u chelonest_timelapse.py
