import os
import time
import sys
import json
import requests
import math  # Import to check for NaN values
import matplotlib.pyplot as plt
from datetime import datetime
import RPi.GPIO as GPIO
from hx711 import HX711
from picamera2 import Picamera2
from tkinter import Tk, Label, Button, Frame
from threading import Thread
from statistics import mean
from collections import Counter
from inference_sdk import InferenceHTTPClient  # Import Roboflow InferenceHTTPClient

# Initialize Roboflow Inference Client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key="7XvsXx7RYeTnwBvj9HH2"
)

BASE_DIR = "/home/xm23917/Desktop/weight/hx711py"
ZERO_READING_FILE = os.path.join(BASE_DIR, "zero_reading.json")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration_data.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
WEIGHT_LOG_FILE = os.path.join(BASE_DIR, "weight_data.json")

# Ensure image directory exists
os.makedirs(IMAGES_DIR, exist_ok=True)

# Nutritionix API credentials
NUTRITIONIX_APP_ID = "94615eef"
NUTRITIONIX_API_KEY = "5e7a357053959ca39c053ba924460cc9"

# Initialize HX711, Camera, and Nutrition Variables
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")
camera = Picamera2()
camera.configure(camera.create_still_configuration())
total_nutrition = {
    "calories": 0,
    "protein": 0,
    "total_fat": 0,
    "saturated_fat": 0,
    "cholesterol": 0,
    "sodium": 0,
    "total_carbohydrate": 0,
    "dietary_fiber": 0,
    "sugars": 0
}

# Initialize global monitoring state
monitoring = False

# Cleanup function to handle exit
def cleanAndExit():
    print("Cleaning up...")
    GPIO.cleanup()
    print("Bye!")
    sys.exit()

# Disable GPIO warnings
GPIO.setwarnings(False)

# Function to get a single weight reading
def get_weight_reading():
    reading = hx.get_weight(5)
    return max(0, reading)  # Ensure no negative values

# Function to calculate the mode-like average within 1g tolerance
def get_mode_average(weights, tolerance=1):
    rounded_weights = [round(w) for w in weights]
    grouped = Counter(rounded_weights)
    most_common_weight = grouped.most_common(1)[0][0]
    mode_group = [w for w in weights if most_common_weight - tolerance <= w <= most_common_weight + tolerance]
    return mean(mode_group) if mode_group else 0

# Function to initialize scale with a new zero reading every time the code runs
def initialize_scale():
    print("Please ensure the scale is empty. Setting zero reading in:")
    for i in range(3, 0, -1):
        print(i)
        time.sleep(1)

    hx.tare()
    zero_reading = hx.get_offset()
    with open(ZERO_READING_FILE, "w") as f:
        json.dump({"zero_reading": zero_reading}, f, indent=4)
    print(f"Zero reading saved for future use in {ZERO_READING_FILE}")

# Function to load the calibration reference unit
def load_reference_unit():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            calibration_data = json.load(f)
        reference_unit = calibration_data["reference_unit"]
        print(f"Loaded reference unit: {reference_unit}")
        hx.set_reference_unit(reference_unit)
    except (FileNotFoundError, KeyError):
        print("Calibration data not found. Please calibrate the scale.")
        reference_unit = reset_calibration()
    return reference_unit

# Function to fetch nutrition info from Nutritionix API
def fetch_nutrition_info(ingredient_name, weight_grams):
    headers = {
        "x-app-id": NUTRITIONIX_APP_ID,
        "x-app-key": NUTRITIONIX_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "query": f"{weight_grams} grams of {ingredient_name}",
        "timezone": "US/Eastern"
    }
    response = requests.post("https://trackapi.nutritionix.com/v2/natural/nutrients", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch nutrition data: {response.status_code}")
        return None

# Function to capture image and log weight with nutrition data
def capture_and_log_image(weight, image_number):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    image_filename = os.path.join(IMAGES_DIR, f"ingredient_{image_number}_{timestamp}.jpg")
    camera.start()
    camera.capture_file(image_filename)
    camera.stop()

    # Use Roboflow API to detect ingredient name
    try:
        result = CLIENT.infer(image_filename, model_id="food-ingredients-detection-qfit7/48")
        predictions = result.get("predictions", [])
        if predictions:
            ingredient_name = predictions[0]["class"]
            print(f"Detected ingredient: {ingredient_name}")
        else:
            ingredient_name = "Unknown"
            print("No ingredient detected.")
    except Exception as e:
        print(f"Error in ingredient detection: {e}")
        ingredient_name = "Unknown"

    # Fetch and accumulate nutrition info
    nutrition_data = fetch_nutrition_info(ingredient_name, weight)
    nutrition_info = {
        "calories": float('nan'),
        "protein": float('nan'),
        "total_fat": float('nan'),
        "saturated_fat": float('nan'),
        "cholesterol": float('nan'),
        "sodium": float('nan'),
        "total_carbohydrate": float('nan'),
        "dietary_fiber": float('nan'),
        "sugars": float('nan')
    }
    if nutrition_data:
        for food in nutrition_data["foods"]:
            for key in nutrition_info.keys():
                # Set the value to NaN if missing, or the actual value if present
                value = food.get(f"nf_{key}", None)
                nutrition_info[key] = float('nan') if value is None else value

                # Accumulate only if the value is a valid number
                if not math.isnan(nutrition_info[key]):
                    total_nutrition[key] += nutrition_info[key]

    # Log weight and ingredient data with nutrition info in JSON format
    log_entry = {
        "ingredient_number": image_number,
        "ingredient_name": ingredient_name,
        "weight": round(weight, 2),
        "timestamp": timestamp,
        "image": image_filename,
        "nutrition_info": nutrition_info
    }

    # Save data to weight_data.json in serial order
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
    print(f"Logged weight and nutrition data for {ingredient_name}: {log_entry}")

# Real-time weight display and auto-capture upon stabilization
def monitor_weight(display_label, stability_threshold=1, stabilization_time=1):
    global monitoring
    last_logged_weight = None
    while True:
        if monitoring:
            start_time = time.time()
            stable_readings = []
            while time.time() - start_time < stabilization_time:
                current_weight = get_weight_reading()
                stable_readings.append(current_weight)
                display_label.config(text=f"Current Weight: {current_weight:.2f} grams")

                # Check if readings are stable within the threshold
                if len(stable_readings) > 1:
                    avg_weight = get_mode_average(stable_readings)
                    if abs(avg_weight - stable_readings[-1]) > stability_threshold:
                        # Reset if the weight becomes unstable
                        stable_readings = []
                        start_time = time.time()  # Reset stabilization timer

                time.sleep(0.05)  # Sampling delay for responsiveness

            # If the weight is stable for the full duration and not zero, capture and log
            if stable_readings and sum(stable_readings) / len(stable_readings) > 0:
                average_stable_weight = sum(stable_readings) / len(stable_readings)
                if last_logged_weight is None or abs(average_stable_weight - last_logged_weight) > stability_threshold:
                    image_number = len(os.listdir(IMAGES_DIR)) + 1
                    capture_and_log_image(average_stable_weight, image_number)
                    display_label.config(text=f"Weight logged: {average_stable_weight:.2f} grams")
                    last_logged_weight = average_stable_weight

                # Prompt to change ingredient after capture
                display_label.config(text="Please change the ingredient.")
                time.sleep(2)
                monitoring = False  # Stop monitoring until next cycle

# Tkinter-based UI for controlling the monitoring
def start_monitoring():
    global monitoring
    monitoring = True

def stop_monitoring():
    global monitoring
    monitoring = False

def main():
    root = Tk()
    root.title("Ingredient Weighing System")

    frame = Frame(root)
    frame.pack()

    weight_display = Label(frame, text="Weight: Not Detected", font=("Helvetica", 16))
    weight_display.grid(row=0, column=0, pady=10)

    start_button = Button(frame, text="Start", command=start_monitoring)
    start_button.grid(row=1, column=0, padx=10, pady=5)

    stop_button = Button(frame, text="Stop", command=stop_monitoring)
    stop_button.grid(row=1, column=1, padx=10, pady=5)

    # Initialize scale before running
    initialize_scale()
    load_reference_unit()

    # Start weight monitoring in a separate thread
    monitoring_thread = Thread(target=monitor_weight, args=(weight_display,))
    monitoring_thread.daemon = True
    monitoring_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()
