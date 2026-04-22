from chelonest_heuristic_registry import register

@register("dwell")
class DwellHeuristic:
    processor = None
    name = None
    threshold = 50
    zone_mem = {}
    mem_depth = 5
    contexts = []
    
    def __init__(self, name="name", processor=None, contexts = [], parameters = {}):
        if "threshold" in parameters:
            self.threshold = parameters["threshold"]
           
        self.contexts = contexts
        self.processor = processor
        self.name = name
        
        self.log(f"Threshold is {self.threshold}")

    def emit(self, data):
        self.processor.plugin_result(self, "dwell", data)

    def log(self, blob):
        self.processor.log(str(self) + f"({self.name}) {blob}")
        
    def detect(self, msg):
        result = {"zones": {} }
        
        for z in msg["zones"]:
            if z not in self.zone_mem:
                self.zone_mem[z] = [ int(msg["zones"][z]) ]
            else:
                self.zone_mem[z].append( int(msg["zones"][z]) )
                if len(self.zone_mem[z]) > self.mem_depth:
                    self.zone_mem[z] = self.zone_mem[z][-self.mem_depth:]
            #emit( { "score": max(all zones), zones: {Z1 .. Z9}
            
            result["zones"][z] = sum(self.zone_mem[z]) / len(self.zone_mem[z])
            result["score"] = max(result["zones"].values())

        return "dwell", result
    