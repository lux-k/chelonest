import cv2
import numpy as np
import json
import time
import sys
import chelonest_config
import paho.mqtt.client as mqtt
import os

CAMERA = None

if len(sys.argv) > 1:
    CAMERA = sys.argv[1]
else:
    CAMERA = "camera"

print("Camera is:", CAMERA)

CONFIG = chelonest_config.load_config()
CAMERA_CONFIG = None

if not CAMERA in CONFIG["cameras"]:
    print("Configuration section for camera",CAMERA,"not found")
    sys.exit(1)
else:
    CAMERA_CONFIG = CONFIG["cameras"][CAMERA]

if not "source" in CAMERA_CONFIG:
    print("Camera configuration source is missing")
    sys.exit(1)

if not CAMERA_CONFIG["motion"]["enabled"]:
    print("Motion detection is disabled in the config")
    sys.exit(1)

FILE = f"{CAMERA}.json"

# grid size
ROWS = CAMERA_CONFIG["motion"]["zones"]["rows"]
COLS = CAMERA_CONFIG["motion"]["zones"]["columns"]

os.makedirs(CONFIG['motion']['output_dir'], exist_ok=True)

print("Zoning is", ROWS, "rows x", COLS, "columns.")

MQTT_CLIENT = None
MQTT_TOPIC = None
if "mqtt" in CAMERA_CONFIG and CAMERA_CONFIG["mqtt"]:
    print("MQTT: Enabled")
    MQTT_CLIENT, MQTT_TOPIC = chelonest_config.mqtt_client(CONFIG, CAMERA + "_detector")
    MQTT_TOPIC = MQTT_TOPIC + "/" + CAMERA + "/motion"
    MQTT_CLIENT.loop_start()
    print("MQTT: Topic", MQTT_TOPIC)
else:
    print("MQTT: Disabled")

# activity threshold per zone (tune later)
ZONE_THRESHOLD = 500

print("Source is:", CAMERA_CONFIG["source"])
cap = cv2.VideoCapture(CAMERA_CONFIG["source"])
print("Source is opened:", cap.isOpened())

fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

def get_zones(frame):
    h, w = frame.shape
    zones = {}
    zh = h // ROWS
    zw = w // COLS
    
    for r in range(ROWS):
        for c in range(COLS):
            name = f"Z{r*COLS + c + 1}"
            y1 = r * zh
            y2 = (r + 1) * zh
            x1 = c * zw
            x2 = (c + 1) * zw
            zones[name] = (y1, y2, x1, x2)

    return zones

def output_zone_image(zones,frame,mask):
    global CAMERA
    global CONFIG
    frame = frame.copy()
    color = (0, 255, 0)

    for name, (y1, y2, x1, x2) in zones.items():
        label = name

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Draw label
        cv2.putText(frame, label, (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # Save image (headless)
    cv2.imwrite(f"{CONFIG['motion']['output_dir']}{CAMERA}_debug_grid.jpg", frame)
    if mask is not None:
        frame = cv2.bitwise_and(frame, frame, mask=mask)
        cv2.imwrite(f"{CONFIG['motion']['output_dir']}{CAMERA}_debug_grid_masked.jpg", frame)
	
def generate_mask(frame):
    if "motion" in CAMERA_CONFIG and "masks" in CAMERA_CONFIG["motion"]:
        print("Masks: Motion mask(s) detected in configuration")
        cv2mask = np.ones(frame.shape[:2], dtype=np.uint8)
        mc = 0
        for mask in CAMERA_CONFIG["motion"]["masks"]:
            if "apply" not in mask or mask["apply"] is True:
                points = []
                for point in mask["points"]:
                    points.append( [ point["x"], point["y"] ] )
                mc += 1
                print(f"Masks: Apply mask", mask["name"])
                cv2.fillPoly(cv2mask, [np.array(points, np.int32)], 0)
        print(f"Masks: {mc} motion masks applied")
        return cv2mask

    else:
        return None
    
zones = None
fps = None
mask = None
delay = 0

last_print = time.time()
json_out = None
if MQTT_CLIENT is not None:
    json_out = open(FILE, "a")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame read failed")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)
            print("FPS is:",fps)
            if CAMERA_CONFIG["source"][:5] != "rtsp:":
                delay = 1.0 / fps
            print("Delay is ",delay)
            # create the mask
            mask = generate_mask(frame)
            zones = get_zones(gray)
            # write out zone img
            output_zone_image(zones, gray, mask)

        if mask is not None:
            gray = cv2.bitwise_and(gray, gray, mask=mask)

        # apply MOG2
        fgmask = fgbg.apply(gray)

        # clean noise
        fgmask = cv2.medianBlur(fgmask, 5)
         
        zone_activity = {}
        total_activity = 0

        for name, (y1, y2, x1, x2) in zones.items():
            region = fgmask[y1:y2, x1:x2]
            activity = cv2.countNonZero(region)
#          if activity < ZONE_THRESHOLD:
#            activity = 0

            zone_activity[name] = activity
            total_activity += activity

        # print every 1 second
        if time.time() - last_print > 1:
            last_print = time.time()

          # filter active zones
            active = {
                k: v for k, v in zone_activity.items()
                if v > ZONE_THRESHOLD
            }

            top = sorted(zone_activity.items(), key=lambda x: x[1], reverse=True)[:3]

            event = {"ts": int(time.time()), "zones": zone_activity}

            if json_out is not None:
                json_out.write(json.dumps(event) + "\n")
                
            if MQTT_CLIENT is not None:
                try:
                    MQTT_CLIENT.publish(MQTT_TOPIC, payload = json.dumps(event), qos = 0, retain = 1 )
                except:
                    print("Error sending to MQTT")
			
#            print("TOTAL:", total_activity)
#            print("ACTIVE:", active)
            print(f"{CAMERA} TOP:", top)
            print("-" * 40)

        if delay > 0:
            time.sleep(delay)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    if json_out is not None:
        json_out.close()