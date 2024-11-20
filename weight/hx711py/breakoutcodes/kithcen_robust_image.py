import time
import sys
import json
import RPi.GPIO as GPIO
from hx711 import HX711

# Cleanup function to handle exit
def cleanAndExit():
    print("Cleaning up...")
    GPIO.cleanup()
    print("Bye!")
    sys.exit()

# Disable GPIO warnings
GPIO.setwarnings(False)

# Initialize HX711
hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")

def get_average_weight(times=5, delay=0.05):
    readings = [hx.get_weight(5) for _ in range(times)]
    time.sleep(delay)
    return max(0, sum(readings) / len(readings))

def reset_calibration():
    hx.tare()
    print("Scale tared. Place a known weight on the scale.")

    while True:
        known_weight = float(input("Enter known weight in grams: "))
        if known_weight > 0:
            break
        else:
            print("Weight must be greater than zero.")

    time.sleep(2)
    raw_value = get_average_weight() - hx.get_offset()
    reference_unit = raw_value / known_weight
    hx.set_reference_unit(reference_unit)

    with open("/home/xm23917/Desktop/weight/hx711py/calibration_data.json", "w") as f:
        json.dump({
            "reference_unit": reference_unit,
            "calibration_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=4)

    print(f"Calibration complete. Reference unit: {reference_unit}")
    return reference_unit

def load_reference_unit():
    try:
        with open("/home/xm23917/Desktop/weight/hx711py/calibration_data.json", "r") as f:
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

def main():
    reference_unit = load_reference_unit()
    print("Ensure scale is empty.")
    initialize_scale()
    print("Scale ready. Add weight.")

    last_weight = 0
    stable_readings = []
    stability_threshold = 1  # Faster threshold
    try:
        while True:
            val = get_average_weight(times=3, delay=0.01)

            if val > 0:
                if not stable_readings or abs(val - stable_readings[-1]) <= stability_threshold:
                    stable_readings.append(val)
                    if len(stable_readings) >= 2:
                        average_stable_weight = sum(stable_readings) / len(stable_readings)
                        print(f"Stabilized Weight: {average_stable_weight:.2f} grams. Taking picture.")
                        
                        with open("/home/xm23917/Desktop/weight/hx711py/weight_data.json", "w") as f:
                            json.dump({
                                "average_weight": average_stable_weight,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }, f, indent=4)
                        hx.tare()
                        print("Place new ingredient.")
                        stable_readings.clear()
                else:
                    stable_readings = [val]

            else:
                if last_weight > 0:
                    print("Weight: 0.00 grams")
                last_weight = 0
                stable_readings.clear()

            hx.power_down()
            hx.power_up()
            time.sleep(1)  # Reduced delay for faster response

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()

if __name__ == "__main__":
    main()
