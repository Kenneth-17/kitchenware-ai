import os
import time
import sys
import json
import RPi.GPIO as GPIO
from hx711 import HX711
from picamera2 import Picamera2
from tkinter import Tk, Label
from threading import Thread
from statistics import mean
from collections import Counter


# Define file paths
BASE_DIR = "/home/xm23917/Desktop/weight/hx711py"
ZERO_READING_FILE = os.path.join(BASE_DIR, "zero_reading.json")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration_data.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
WEIGHT_LOG_FILE = os.path.join(BASE_DIR, "weight_data.json")

# Ensure image directory exists
os.makedirs(IMAGES_DIR, exist_ok=True)

# Initialize HX711 and Camera
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")
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

# Function to capture image and log weight
def capture_and_log_image(weight, image_number):
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    image_filename = os.path.join(IMAGES_DIR, f"weight_{image_number}_{int(weight)}_{timestamp}.jpg")
    camera.start()
    camera.capture_file(image_filename)
    camera.stop()

    # Log weight data in JSON format
    log_entry = {
        "image_number": image_number,
        "weight": round(weight, 2),
        "timestamp": timestamp,
        "image": image_filename
    }

    # Save data to weight_data.json
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
    print(f"Logged weight data: {log_entry}")

# Real-time weight display and auto-capture upon stabilization
def monitor_weight(display_label, stability_threshold=1, stabilization_time=1):
    last_logged_weight = None
    capturing = False

    while True:
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
                capturing = True

            # Prompt to change ingredient after capture
            if capturing:
                display_label.config(text="Please change the ingredient and wait...")
                time.sleep(2)
                while get_weight_reading() != 0:
                    time.sleep(0.1)  # Wait until scale is empty
                display_label.config(text="Add next ingredient...")
                capturing = False

# Tkinter GUI setup
def start_gui():
    root = Tk()
    root.title("Real-Time Weighing Scale")
    root.geometry("400x200")
    
    # Weight display label
    display_label = Label(root, text="Initializing...", font=("Helvetica", 18), fg="green")
    display_label.pack(pady=20)

    # Start real-time weight monitoring and auto-capture in a separate thread
    Thread(target=monitor_weight, args=(display_label,), daemon=True).start()

    root.mainloop()

# Main function
def main():
    load_reference_unit()
    initialize_scale()  # Set new zero reading at start
    print("Scale ready. Starting real-time GUI with auto-capture on stabilization...")
    start_gui()

if __name__ == "__main__":
    main()
