import os
import cv2
import datetime
import time
import subprocess
import re
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
from datetime import datetime
import pytz

# RTSP stream URL
rtsp_url = "rtsp://admin:AZTTNA@192.168.1.15:554/ch1/main"

# Set constant values for plantId and plcId
plant_id = ""
plc_id = ""

# Function to get the current timestamp in the desired format
def get_current_timestamp():
    local_now = datetime.now()
    india_timezone = pytz.timezone('Asia/Kolkata')
    now_india = local_now.astimezone(india_timezone)
    return now_india.strftime('%d-%m-%YT%H-%M')

# Function to capture an image from the RTSP stream
def take_photo():
    images_dir = "/Users/nalinluthra/Code/results"
    os.makedirs(images_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_file = os.path.join(images_dir, f'{timestamp}.jpg')
    
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(3, 3840)  # Width
    cap.set(4, 2600)  # Height
    
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_file, frame)
    cap.release()

    return output_file if ret else None

# Function to run Darknet and return bounding box coordinates
def run_darknet(image_path):
    result = subprocess.run(["./darknet.py", "detector", "test", "data/obj.data", "cfg/yolov4-obj.cfg", "yolov4-obj_final.weights", "-dont_show", "-ext_output", image_path], stdout=subprocess.PIPE, text=True)
    output = result.stdout

    beaker_match = re.findall(r"Beaker: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)
    sludge_match = re.findall(r"Sludge: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)

    return beaker_match, sludge_match

# Function to calculate sludge level percentage
def calculate_sludge_percentage(beaker_bbox, sludge_bbox):
    beaker_height = beaker_bbox[3]
    sludge_height = sludge_bbox[3]
    sludge_level_percentage = ((120 /beaker_height) * sludge_height)
    return sludge_level_percentage

# AWS IoT configurations
host = "a1uci4yrmbdj5m-ats.iot.ap-south-1.amazonaws.com"
root_ca_path = "/Users/nalinluthra/Code/Certificates/AmazonRootCA1.pem"
certificate_path = "/Users/nalinluthra/Code/Certificates/817f7a52521008a5ee35675333a01e7dafc01c8f742db2121161cd9c264b37b4-certificate.pem.crt"
private_key_path = "/Users/nalinluthra/Code/Certificates/817f7a52521008a5ee35675333a01e7dafc01c8f742db2121161cd9c264b37b4-private.pem.key"
port = 8883
client_id = "NALIN_PLC_1"
topic = "nalin/pub"

# Initialize and configure AWS IoT MQTT Client
my_aws_iot_mqtt_client = AWSIoTMQTTClient(client_id)
my_aws_iot_mqtt_client.configureEndpoint(host, port)
my_aws_iot_mqtt_client.configureCredentials(root_ca_path, private_key_path, certificate_path)
my_aws_iot_mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
my_aws_iot_mqtt_client.configureOfflinePublishQueueing(-1)
my_aws_iot_mqtt_client.configureDrainingFrequency(2)
my_aws_iot_mqtt_client.configureConnectDisconnectTimeout(10)
my_aws_iot_mqtt_client.configureMQTTOperationTimeout(5)

# Connect to AWS IoT
my_aws_iot_mqtt_client.connect()

array_of_data = []

# Set the limit of array to 10
limit = 10

# Set starting time
start_time = time.time()

# Main loop
while True:
    photo_path = take_photo()
    if photo_path:
        beaker_bbox, sludge_bbox = run_darknet(photo_path)
        beaker_bbox = [int(x) for x in beaker_bbox[0]]
        sludge_bbox = [int(x) for x in sludge_bbox[0]]
        if not beaker_bbox or not sludge_bbox:
            sludge_level_percentage = 0
        else:
            sludge_level_percentage = calculate_sludge_percentage(beaker_bbox, sludge_bbox)
            print(f"Detection failed for image {photo_path}")

        timestamp = datetime.now().isoformat()

        array_of_data.append({
            "beaker_bbox": beaker_bbox,
            "sludge_bbox": sludge_bbox,
            "sludge_level_percentage": sludge_level_percentage,
            "timestamp": timestamp
        })
        if len(array_of_data) == limit:
            number_of_times_beaker_detected = sum([1 for data in array_of_data if data["beaker_bbox"]])

            # Reset the start time
            if number_of_times_beaker_detected == 0:
                print("Beaker not detected in any of the images")
                start_time = time.time()
                continue
            
            average_sludge_level_percentage = sum([data["sludge_level_percentage"] for data in array_of_data]) / number_of_times_beaker_detected

            # Assuming sludge_level_percentage is calculated in your script
            sludge_level_percentage = round(sludge_level_percentage, 2)  # rounding to two decimal places

            # Remove first element from the array
            array_of_data.pop(0)

            # 30 Mins have passed from starting time
            minutes_passed = (time.time() - start_time) / 60
            
            if minutes_passed >= 29 and minutes_passed <= 31:
                print("30 minutes have passed")
                # Prepare the data dictionary
            elif minutes_passed >= 59 and minutes_passed <= 61:
                print("60 minutes have passed")
                # Prepare the data dictionary
            elif minutes_passed >= 89 and minutes_passed <= 91:
                print("900 minutes have passed")
                # Prepare the data dictionary

                # Preparing the data dictionary
                data = {
                    "plantId": plant_id,
                    "plcId": plc_id,
                    "TIMESTAMP": get_current_timestamp(),
                    "SV30_ATdd1_1": str(average_sludge_level_percentage)  # Converting float to string
                }

                # Convert the dictionary to JSON
                json_data = json.dumps(data, indent=4)
                print(json_data)

                my_aws_iot_mqtt_client.publish(topic, json_data, 1)
                print(f"Data published to AWS IoT: {json_data}")

                # Reset the start time
                

            # Preparing the data dictionary
            data = {
                "plantId": plant_id,
                "plcId": plc_id,
                "TIMESTAMP": get_current_timestamp(),
                "SV30_ATdd1_1": str(sludge_level_percentage)  # Converting float to string
            }

            # Convert the dictionary to JSON
            json_data = json.dumps(data, indent=4)
            print(json_data)

            my_aws_iot_mqtt_client.publish(topic, json_data, 1)
            print(f"Data published to AWS IoT: {json_data}")
    else:
        print("Failed to capture image")

my_aws_iot_m
