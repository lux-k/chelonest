import os
import time
from datetime import datetime
import chelonest_config
import subprocess
import urllib.request
import shutil

CONFIG = chelonest_config.load_config()

TL_CONFIG = CONFIG["timelapse"]
print(TL_CONFIG)

print("Timelapse: frame delay", TL_CONFIG["period"])
print("Timelapse: start hour", TL_CONFIG["start_hour"])

os.makedirs(TL_CONFIG["output_dir"], exist_ok = True)
os.chdir(TL_CONFIG["output_dir"])

os.makedirs(TL_CONFIG["webcam_dir"], exist_ok = True)

def make_rtsp_command(camera, conf):
    command = None
    if conf["source"][:5] == "rtsp:":
        count = None
        try:
            count = str(int(subprocess.check_output('ls snaps/' + camera + '/*.jpg | wc -l', shell=True).decode('utf-8')))
        except subprocess.CalledProcessError as err:
            count = 0
        finally:
            print("Timelapse:",camera,"start number",count);
       
        overlay = conf["timelapse"]["overlay"]
       
        command = ["ffmpeg", "-y", "-rtsp_transport", "tcp", "-nostats", "-use_wallclock_as_timestamps", "1", "-i", conf["source"],
        "-filter_complex", "fps=1/" + str(TL_CONFIG["period"]) + ",scale=704:480,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:" + overlay + ":fontsize=18:fontcolor=white:box=1:boxcolor=0x00000099,split=2[series][webcam]",
        "-start_number", count, "-map","[series]", "-vsync","vfr","snaps/" + camera + "/%06d.jpg",
        "-map","[webcam]","-vsync","vfr","-update", "1", TL_CONFIG["webcam_dir"] + "/" + camera + ".jpg"]

    return command

WORKQUEUE = []
CUR_ITEM = None
CAMERAS = {}
try:
    while True:
        count = 0
        # Get current date and time
        end_hour = CONFIG["timelapse"]["start_hour"]
        #$endhour = 19 if $starthour >= 7 && $starthour < 19;
        if datetime.now().hour >= CONFIG["timelapse"]["start_hour"] and datetime.now().hour < (CONFIG["timelapse"]["start_hour"] + 12):
            end_hour += 12
        print("Timelapse: period ends", end_hour)
        DATE = datetime.now().strftime("%Y-%m-%d-%p")
        print("Timelapse: date period", DATE)

        for camera in CONFIG["cameras"]:
            if "timelapse" in CONFIG["cameras"][camera]:
                if not "enabled" in CONFIG["cameras"][camera]["timelapse"] or not CONFIG["cameras"][camera]["timelapse"]["enabled"]:
                    continue
                
                print("Timelapse: enable camera", camera)
                os.makedirs("snaps/" + camera, exist_ok = True)
                os.makedirs("movies/" + camera, exist_ok = True)
                command = make_rtsp_command(camera, CONFIG["cameras"][camera])
                CAMERAS[camera] = {"source": CONFIG["cameras"][camera]["source"], "command": command, "process": None}
        
        while datetime.now().hour != end_hour:        
        #while count < 6:
            for camera in CAMERAS:
                if CAMERAS[camera]["command"] is not None and (CAMERAS[camera]["process"] is None or CAMERAS[camera]["process"].poll() is not None):
                    #rtsp based
                    print("Camera:", camera, "start process")
                    CAMERAS[camera]["process"] = subprocess.Popen(CAMERAS[camera]["command"])
                elif CAMERAS[camera]["command"] is None:
                    #image based
                    print("Camera:", camera, "retrieve",CAMERAS[camera]["source"])
                    try:
                        urllib.request.urlretrieve(CAMERAS[camera]["source"], "snaps/" + camera + "/" + str(int(time.time())) + ".jpg")
                    except Exception as e:
                        print(e)
            
            if len(WORKQUEUE) > 0 and (CUR_ITEM is None or CUR_ITEM.poll() is not None):
                cmd = WORKQUEUE.pop(0)
                print("Timelapse: process command ", cmd)
                CUR_ITEM = subprocess.Popen(cmd, shell=True)
                
            time.sleep(TL_CONFIG["period"])
            count = count + 1
            #at this point, we have both images and rtsp streaming

        #we get to this point, it's because we're with that segment.
        #firstly, kill all the ffmpeg sessions
        for camera in CAMERAS:
            if CAMERAS[camera]["command"] is not None and CAMERAS[camera]["process"].poll() is None:
                CAMERAS[camera]["process"].terminate()

        #now we move the files
        for camera in CAMERAS:
            shutil.move("snaps/"+camera,"snaps/"+camera+"_last")
            WORKQUEUE.append("ffmpeg -y -f image2 -framerate 8 -pattern_type glob -i 'snaps/" + camera + "_last" + "/*.jpg' -s 704x480 -c:v libvpx-vp9 -b:v 0 -crf 32 -row-mt 1 -threads 4 -pix_fmt yuv420p movies/" + camera + "/" + DATE + ".webm");
            WORKQUEUE.append("rm -rf snaps/" + camera + "_last");

except Exception as e:
    print(e)
finally:
    print("Stopping...")
    for camera in CAMERAS:
        if CAMERAS[camera]["command"] is not None and CAMERAS[camera]["process"].poll() is None:
            CAMERAS[camera]["process"].terminate()

