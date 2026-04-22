from chelonest_heuristic_registry import registry
import chelonest_config
import time
import sys
import json
import requests

#this is the global config
CONFIG = chelonest_config.load_config()

CAMERA = "spotteds-local"
CAMERA = "boxies"

class HeuristicProcessor:
    _config = None
    _instances = None
    current_frame = None
    last_frame = None
    
    def __init__(self):
        registry._processor = self
        self._set_config()
        registry.load_heuristic_modules()
        self.log("loaded heuristics " + str(registry.HEURISTICS))
        self.load_heuristic_instances()
        
    def update(self, ts, zones):
        print("hello")

    def log(self, blob):
        print("Heuristics:", blob)
        
    def init_plugins(self):
        print("meh")
        
    def _set_config(self):
        if not CAMERA in CONFIG["cameras"]:
            self.log("Camera " + CAMERA + " not found in config")
            sys.exit(1)

        if not "heuristics" in CONFIG["cameras"][CAMERA]:
            self.log("No heuristics defined for camera " + CAMERA)
            sys.exit(1)

        self._config = CONFIG["cameras"][CAMERA]
     
    def camera_config(self):
        return self._config

    def load_heuristic_instances(self):
        self._instances = registry.load_heuristic_instances(self._config["heuristics"])
        print(self._instances)

    def plugin_result(self, plugin, detection, data):
        print("whee")
        
    def send_motion_data(self, msg):
        self.last_frame = self.current_frame
        
        new_frame = {}
        if self.last_frame is not None:
            for state in self.last_frame:
                if state in self.last_frame:
                    new_frame[state] = {"score": self.last_frame[state]["score"], "components": {}}
                    if state in self.camera_config()["state_decay"]:
                        new_frame[state]["score"] *= self.camera_config()["state_decay"][state]
                    
        
        for h in self._instances:
            if "detect" in h.contexts:
                state, result = h.detect(msg)
                if state not in new_frame:
                    new_frame[state] = {"score": result["score"], "components": {}}
                else:
                    new_frame[state]["score"] += result["score"]
                new_frame[state]["components"][h.name] = result

        #aggregate
        for h in self._instances:
            if "aggregate" in h.contexts:
                h.aggregate(msg)
        
        self.current_frame = new_frame
        print(self.current_frame)
        
    def integration_configured(self, section, keys):
        if not "integrations" in CONFIG:
            self.log("No integrations defined.")
            return None
            
        if not section in CONFIG["integrations"]:
            self.log("Integration " + section + " has no configuration.")
            return None

        ret_val = CONFIG["integrations"][section]
        for k in keys:
            if not k in CONFIG["integrations"][section]:
                self.log("Integration " + section + " is missing required value " + k)
                ret_val = None
        
        return ret_val
        
    def frigate_event(self, event, params=None):
        #https://docs.frigate.video/integrations/api/create-event-events-camera-name-label-create-post/
        
        conf = self.integration_configured("frigate",["url"])
        
        if conf is None:
            self.log("Unable to post to frigate; configuration incomplete")
        else:
            try:
                url = conf["url"] + "api/events/" + self._config["frigate_name"] + "/" + event + "/create"
                if params is None:
                    params = {"duration": 15}
                 
                r = requests.post(url, json=params)
                self.log("posted " + event + " to frigate")
            except Exception as e:
                self.log("posting to frigate failed - " + str(e))
                
    def pushover_send(self, msg):
        conf = self.integration_configured("pushover",["app_token", "user_key"])
        if conf is None:
            self.log("Unable to post to Pushover; configuration incomplete")
        else:
            url = "https://api.pushover.net/1/messages.json"
            params = {"token": conf["app_token"], "user": conf["user_key"], "message": msg}
            try:
                r = requests.post(url, json=params)
                self.log("posted " + msg + " to pushover")
            except Exception as e:
                self.log("posting to pushover failed - " + str(e))

processor = HeuristicProcessor()
#processor.frigate_event('nesting', {"score": .92, "duration": 15})
msg = {"ts": 0, "zones": {"Z1": 0, "Z2": 20, "Z3": 0, "Z4": 0, "Z5": 20, "Z6": 0, "Z7": 0, "Z8": 20, "Z9": 0,}}
processor.send_motion_data(msg)
processor.send_motion_data(msg)
processor.send_motion_data(msg)
processor.send_motion_data(msg)
processor.send_motion_data(msg)
processor.send_motion_data(msg)
processor.send_motion_data(msg)
sys.exit(0)

client, topic = chelonest_config.mqtt_client(CONFIG, CAMERA + "_heuristic_processor", [CAMERA + "/#"])
def on_message(client, userdata, message):
    # userdata is the structure we choose to provide, here it's a list()
    msg = json.loads(message.payload)
    print("Received", msg)
    processor.send_motion_data(msg)


    
client.on_message = on_message
client.loop_forever()