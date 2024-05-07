import os
import cv2
import datetime
import time
import subprocess
import re

# RTSP stream URL
#rtsp_url = "rtsp://admin:NXKWMS@192.168.1.41:554/ch1/main"
rtsp_url = "rtsp://admin:QKEHUX@192.168.1.25:554/ch1/main"

# Function to run Darknet and return bounding box coordinates
def run_darknet(image_path):
    result = subprocess.run(["./darknet", "detector", "test", "data/obj.data", "cfg/yolov4-obj.cfg", "yolov4-obj_final.weights", "-dont_show", "-ext_output", image_path], stdout=subprocess.PIPE, text=True)
    output = result.stdout

    # Extract bounding box coordinates using regular expressions
    beaker_match = re.findall(r"Beaker: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)
    sludge_match = re.findall(r"Sludge: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)

    return beaker_match, sludge_match

# Function to calculate sludge level percentage
def calculate_sludge_percentage(beaker_bbox, sludge_bbox):
    beaker_height = beaker_bbox[3]
    sludge_height = sludge_bbox[3]
    sludge_level_percentage =  ((120 /beaker_height) * sludge_height)
    return sludge_level_percentage

# Function to capture an image from the RTSP stream
def take_photo():
    # Directory to save captured images
    images_dir = "/home/pi/Testing3"
    os.makedirs(images_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_file = os.path.join(images_dir, f'{timestamp}.jpg')
    
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(3, 3840)  # Width
    cap.set(4, 2600)  # Height
    
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(output_file, frame)
    cap.release()

    return output_file if ret else None

# Main loop
while True:
    photo_path = take_photo()
    if photo_path:
        print(f"Photo captured: {photo_path}")

        # Process the image
        beaker_bbox, sludge_bbox = run_darknet(photo_path)
        if beaker_bbox and sludge_bbox:
            beaker_bbox = [int(x) for x in beaker_bbox[0]]
            sludge_bbox = [int(x) for x in sludge_bbox[0]]

            sludge_level_percentage = calculate_sludge_percentage(beaker_bbox, sludge_bbox)

            # Read and annotate the image
            image = cv2.imread(photo_path)
            cv2.rectangle(image, (beaker_bbox[0], beaker_bbox[1]), (beaker_bbox[0] + beaker_bbox[2], beaker_bbox[1] + beaker_bbox[3]), (0, 255, 0), 2)
            cv2.rectangle(image, (sludge_bbox[0], sludge_bbox[1]), (sludge_bbox[0] + sludge_bbox[2], sludge_bbox[1] + sludge_bbox[3]), (255, 0, 0), 2)
            cv2.putText(image, f"Sludge Level: {sludge_level_percentage:.2f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Save annotated image
            cv2.imwrite(photo_path, image)
        else:
            print(f"Detection failed for image {photo_path}")

    # Wait for 60 seconds
    time.sleep(60)
