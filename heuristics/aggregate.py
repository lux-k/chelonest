from chelonest_heuristic_registry import register
import time

@register("aggregate")
class AggregateHeuristic:
    processor = None
    name = None
    threshold = 50
    iterations = 10
    frames = 0
    last_alert = 0
    zone_mem = {}
    mem_depth = 5
    contexts = []
    
    def __init__(self, name="name", processor=None, contexts = [], parameters = {}):
        if "threshold" in parameters:
            self.threshold = parameters["threshold"]
           
        if "iterations" in parameters:
            self.iterations = parameters["iterations"]

        self.contexts = contexts
        self.processor = processor
        self.name = name
        
        self.log(f"Threshold is {self.threshold}")

    def emit(self, data):
        self.processor.plugin_result(self, "dwell", data)

    def log(self, blob):
        self.processor.log(str(self) + f"({self.name}) {blob}")
        
    def aggregate(self, frame):
        if frame["dwell"]["score"] > self.threshold:
            self.frames += 1
        elif self.frames > 0:
            self.frames -= 1

        if self.frames >= self.iterations and time.time() > (self.last_alert + 300):
            self.log("alert")
            self.processor.pushover_send("heuristic triggered for " + self.name + " score " + str(frame["dwell"]["score"]) + " iterations " + str(self.frames))
            self.last_alert = time.time()
            self.frames = 0