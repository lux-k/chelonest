import json
import time
import sys
import chelonest_config
import subprocess


def main():
    
    CONFIG = chelonest_config.load_config()

    MODE = "detectors"

    if len(sys.argv) > 1:
        MODE = sys.argv[1]

    print("Mode is ", MODE)

    active_cams = {}

    for camera in CONFIG["cameras"]:
        if CONFIG["cameras"][camera]["motion"]["enabled"]:
            active_cams[camera] = {}
 
    while True:
        try:
            while True:
                for c in active_cams:
                    if "process" not in active_cams[c]:
                        print(f"No process for camera {c}.. start")
                        if MODE == "detectors":
                            active_cams[c]["cmd"] = ["python", "-u", "chelonest_detector.py", c]
                        elif MODE == "heuristics":
                            active_cams[c]["cmd"] = ["python", "-u", "chelonest_heuristic_processor.py", c]
                        print("Executing", active_cams[c]["cmd"])
                        active_cams[c]["process"] = subprocess.Popen(active_cams[c]["cmd"])
                    elif active_cams[c]["process"].poll() is not None:
                        print(f"Camera process for camera {c} terminated; restart")
                        active_cams[c]["process"] = subprocess.Popen(active_cams[c]["cmd"])

                
                time.sleep(15)
    
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            print("Stopping...")
            for c in active_cams:
                if "process" in active_cams[c] and active_cams[c]["process"] is not None:
                    print(f"Terminate process for {c}")
                    active_cams[c]["process"].terminate()
            break    

if __name__ == "__main__":
    main()