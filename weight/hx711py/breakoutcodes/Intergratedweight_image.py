import os
import time
import sys
import json
import RPi.GPIO as GPIO
from hx711 import HX711
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFont

# Define paths for images and calibration
BASE_DIR = "/home/xm23917/Desktop/weight/hx711py"
IMAGES_DIR = os.path.join(BASE_DIR, "images")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration_data.json")
WEIGHT_LOG_FILE = os.path.join(BASE_DIR, "weight_data.json")

# Initialize HX711
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")

# Initialize PiCamera2 only when capturing images
camera = Picamera2()
camera.configure(camera.create_still_configuration())

# Cleanup function to handle exit
def cleanAndExit():
    print("Cleaning up...")
    GPIO.cleanup()
    print("Bye!")
    sys.exit()

# Disable GPIO warnings
GPIO.setwarnings(False)

def get_weight_reading(samples=10, delay=0.01):
    """Get a robust weight reading using median and average filtering."""
    readings = [hx.get_weight(5) for _ in range(samples)]
    time.sleep(delay)
    readings.sort()
    median = readings[len(readings) // 2]
    average = sum(readings) / len(readings)
    return max(0, (median + average) / 2)  # Average of median and mean for stability

def reset_calibration():
    hx.tare()
    print("Scale tared. Place a known weight on the scale.")

    while True:
        try:
            known_weight = float(input("Enter known weight in grams: "))
            if known_weight > 0:
                break
            else:
                print("Weight must be greater than zero.")
        except ValueError:
            print("Invalid input. Please enter a numerical value for the weight.")

    time.sleep(2)
    raw_value = get_weight_reading() - hx.get_offset()
    reference_unit = raw_value / known_weight
    hx.set_reference_unit(reference_unit)

    with open(CALIBRATION_FILE, "w") as f:
        json.dump({
            "reference_unit": reference_unit,
            "calibration_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=4)

    print(f"Calibration complete. Reference unit: {reference_unit}")
    return reference_unit

def load_reference_unit():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            reference_unit = json.load(f)["reference_unit"]
        hx.set_reference_unit(reference_unit)
        print(f"Loaded reference unit: {reference_unit}")
    except (FileNotFoundError, KeyError):
        print("No calibration data found. Starting calibration...")
        reference_unit = reset_calibration()
    return reference_unit

def initialize_scale():
    hx.reset()
    hx.tare()
    print("Taring the scale... Please wait for stability.")
    time.sleep(2)

def get_next_image_number():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    existing_images = [f for f in os.listdir(IMAGES_DIR) if f.startswith("weight_") and f.endswith(".jpg")]
    return len(existing_images) + 1

def capture_image(weight, timestamp, image_number):
    camera.start()
    image_filename = os.path.join(IMAGES_DIR, f"weight_{image_number}_{int(weight)}_{timestamp}.jpg")
    camera.capture_file(image_filename)
    print(f"Captured image: {image_filename}")

    # Open the captured image and add the weight text
    with Image.open(image_filename) as img:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font = ImageFont.load_default()

        text = f"Weight: {weight:.2f} grams"
        text_position = (10, 10)
        draw.text(text_position, text, fill="white", font=font)
        img.save(image_filename)
        img.show()

    camera.stop()
    return image_filename

def log_weight_data(weight, timestamp, image_path, image_number):
    log_entry = {
        "image_number": image_number,
        "average_weight": weight,
        "timestamp": timestamp,
        "image": image_path
    }

    try:
        data = []
        if os.path.exists(WEIGHT_LOG_FILE):
            with open(WEIGHT_LOG_FILE, "r") as f:
                data = json.load(f)
    except json.JSONDecodeError:
        print("Warning: JSON file empty or corrupt, initializing new log.")

    data.append(log_entry)
    with open(WEIGHT_LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("Logged weight and image data.")

def main():
    reference_unit = load_reference_unit()
    initialize_scale()
    print("Scale ready. Add weight.")

    stability_threshold = 5
    consecutive_stable_count = 2
    max_variance = 3

    try:
        while True:
            val = get_weight_reading(samples=10, delay=0.001)
            print(f"Current weight: {val:.2f} grams")

            stable_readings = [val]
            if len(stable_readings) >= consecutive_stable_count:
                average_stable_weight = sum(stable_readings) / len(stable_readings)
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                image_number = get_next_image_number()

                image_path = capture_image(average_stable_weight, timestamp, image_number)
                log_weight_data(average_stable_weight, timestamp, image_path, image_number)

                hx.tare()
                print("Place new ingredient.")
                stable_readings.clear()

            hx.power_down()
            hx.power_up()
            time.sleep(0.3)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()

if __name__ == "__main__":
    main()
