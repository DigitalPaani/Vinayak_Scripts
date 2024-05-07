import os
import cv2
import re
import subprocess

def run_darknet(image_path):
    result = subprocess.run(["./darknet", "detector", "test", "data/obj.data", "cfg/yolov4-obj.cfg", "yolov4-obj_final.weights", "-dont_show", "-ext_output", image_path], stdout=subprocess.PIPE, text=True)
    output = result.stdout

    # Parse output for bounding boxes
    beaker_match = re.findall(r"Beaker: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)
    sludge_match = re.findall(r"Sludge: \d+%.*left_x: *(\d+) *top_y: *(\d+) *width: *(\d+) *height: *(\d+)", output)

    return beaker_match, sludge_match

def calculate_sludge_percentage(beaker_bbox, sludge_bbox):
    beaker_height = beaker_bbox[3]
    sludge_height = sludge_bbox[3]
    return ((120 /beaker_height) * sludge_height)

# Update paths according to your Raspberry Pi directory structure
images_dir = "/home/pi/Testing2"
result_dir = "/home/pi/Result2"

for img_name in os.listdir(images_dir):
    img_path = os.path.join(images_dir, img_name)
    result_img_path = os.path.join(result_dir, img_name)
    result_txt_path = os.path.join(result_dir, f"{img_name[:-4]}_result.txt")

    beaker_bbox, sludge_bbox = run_darknet(img_path)

    if beaker_bbox and sludge_bbox:
        beaker_bbox = [int(x) for x in beaker_bbox[0]]
        sludge_bbox = [int(x) for x in sludge_bbox[0]]

        sludge_level_percentage = calculate_sludge_percentage(beaker_bbox, sludge_bbox)

        image = cv2.imread(img_path)
        cv2.rectangle(image, (beaker_bbox[0], beaker_bbox[1]), (beaker_bbox[0] + beaker_bbox[2], beaker_bbox[1] + beaker_bbox[3]), (0, 255, 0), 2)
        cv2.rectangle(image, (sludge_bbox[0], sludge_bbox[1]), (sludge_bbox[0] + sludge_bbox[2], sludge_bbox[1] + sludge_bbox[3]), (255, 0, 0), 2)
        cv2.putText(image, f"Sludge Level: {sludge_level_percentage:.2f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imwrite(result_img_path, image)

        with open(result_txt_path, "w") as f:
            f.write(f"Sludge Level: {sludge_level_percentage:.2f}%\n")
            f.write(f"Beaker bbox: {beaker_bbox}\n")
            f.write(f"Sludge bbox: {sludge_bbox}\n")
    else:
        print(f"Detection failed for image {img_name}")
