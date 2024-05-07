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
rtsp_url = "rtsp://admin:QKEHUX@192.168.1.25:554/ch1/main"

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
    images_dir = "/home/pi/results"
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
    result = subprocess.run(["./darknet", "detector", "test", "data/obj.data", "cfg/yolov4-obj.cfg", "yolov4-obj_final.weights", "-dont_show", "-ext_output", image_path], stdout=subprocess.PIPE, text=True)
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
root_ca_path = "/home/pi/certificates/AmazonRootCA1.pem"
certificate_path = "/home/pi/certificates/certificate.pem.crt"
private_key_path = "/home/pi/certificates/private.pem.key"
port = 8883
client_id = "WorldSpa_SV30_1"
topic = "worldspa/pub"

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

# Main loop
while True:
    photo_path = take_photo()
    if photo_path:
        beaker_bbox, sludge_bbox = run_darknet(photo_path)
        if beaker_bbox and sludge_bbox:
            beaker_bbox = [int(x) for x in beaker_bbox[0]]
            sludge_bbox = [int(x) for x in sludge_bbox[0]]

            sludge_level_percentage = calculate_sludge_percentage(beaker_bbox, sludge_bbox)
            timestamp = datetime.now().isoformat()

            # Assuming sludge_level_percentage is calculated in your script
            sludge_level_percentage = round(sludge_level_percentage, 2)  # rounding to two decimal places
            
            # Annotate image
            image = cv2.imread(photo_path)
            #cv2.rectangle(image, (beaker_bbox[0], beaker_bbox[1]), (beaker_bbox[0] + beaker_bbox[2], beaker_bbox[1] + beaker_bbox[3]), (0, 255, 0), 2)
            #cv2.rectangle(image, (sludge_bbox[0], sludge_bbox[1]), (sludge_bbox[0] + sludge_bbox[2], sludge_bbox[1] + sludge_bbox[3]), (255, 0, 0), 2)
            cv2.putText(image, f"Sludge Level: {sludge_level_percentage:.2f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Save annotated image
            cv2.imwrite(photo_path, image)

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
            print(f"Detection failed for image {photo_path}")

    time.sleep(40)#Wait for 1 seconds

my_aws_iot_m
