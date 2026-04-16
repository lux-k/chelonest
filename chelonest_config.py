import json
from dotenv import load_dotenv
import os
import paho.mqtt.client as mqtt

load_dotenv()

CHELONEST_VER = "0.1"
CONFIG_FILE = os.getenv("CHELONEST_CONFIG_FILE","config.json")

print("Chelonest v", CHELONEST_VER)
print("Config:", CONFIG_FILE)

def load_config():
    if not os.path.isfile(CONFIG_FILE):
        print("Config file is not found.")
        sys.exit(1)

    # Use 'with' to ensure the file is properly closed
    with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
        data = json.load(file)

    if not "cameras" in data:
        print("Configuration file has no cameras defined.")
        sys.exit(1)

    set_defaults_timelapse(data)
    set_defaults_integrations(data)
 
    for name in data["cameras"]:
        set_defaults_detection(data["cameras"][name])
    return data
  
def set_defaults_timelapse(CONFIG):
    TL_DEF = {"period": 30, "enabled": False, "start_hour": 7, "output_dir": "/mnt/timelapse", "webcam_dir": "webcam"}
    if  "timelapse" in CONFIG:
        for k in TL_DEF:
            if not k in CONFIG["timelapse"]:
                CONFIG["timelapse"][k] = TL_DEF[k]
    else:
        CONFIG["timelapse"] = TL_DEF
        
def set_defaults_detection(CONFIG):
    ROWS = 3
    COLS = 3
    
    if "motion" in CONFIG:
        if "zones" in CONFIG["motion"]:
            if not "rows" in CONFIG["motion"]["zones"]:
                CONFIG["motion"]["zones"]["rows"] = ROWS
            if not "columns" in CONFIG["motion"]["zones"]:
                CONFIG["motion"]["zones"]["columns"] = COLS
        else:
            CONFIG["motion"]["zones"] = {"rows": ROWS, "columns": COLS}
            
    else:
        CONFIG["motion"] = {"zones": {"rows": ROWS, "columns": COLS}}

def set_defaults_integrations(CONFIG):
    FRIG_DEF = {"url": "http://localhost:5000"}
    MQTT_DEF = {"host": "localhost", "topic": "chelonest"}
    
    INT_MAP = {"frigate": FRIG_DEF, "mqtt": MQTT_DEF}
    
    if "integrations" in CONFIG:
        for k in INT_MAP:
            if k in CONFIG["integrations"]:
                for ks in INT_MAP[k]:
                    if not ks in CONFIG["integrations"][k]:
                        CONFIG["integrations"]["mqtt"][ks] = INT_MAP[k][ks]
            else:
                CONFIG["integrations"][k] = INT_MAP[k]
    else:
        for k in INT_MAP:
            CONFIG["integrations"][k] = INT_MAP[k]
    
def mqtt_client(CONFIG, clientid="chelonest_client", subs=None):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=clientid, userdata=None)
    topic = None
    def on_disconnect(client, userdata, rc):
        logging.info("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            logging.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("%s. Reconnect failed. Retrying...", err)
    
            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
    
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("MQTT: Connected")
            if subs is not None:
                for s in subs:
                    ssub = topic + '/' + s
                    print("sub", ssub)
                    client.subscribe(ssub)
        else:
            print("MQTT: Failed to connect, return code %d\n", rc)        
    
    #client.on_disconnect = on_disconnect
    client.on_connect = on_connect
    
    if "integrations" in CONFIG and "mqtt" in CONFIG["integrations"]:
        print("MQTT: Host is", CONFIG["integrations"]["mqtt"]["host"])
        topic = CONFIG["integrations"]["mqtt"]["topic"]
        print("MQTT: Base topic is", topic)
        client.connect(CONFIG["integrations"]["mqtt"]["host"])
    else:
        print("MQTT configuration missing.")

    return client, topic