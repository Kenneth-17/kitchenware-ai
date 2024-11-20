import time
import sys
import json
import RPi.GPIO as GPIO
from hx711 import HX711

# Cleanup function to handle exit
def cleanAndExit():
    print("Cleaning up...")
    GPIO.cleanup()  # Clean up the GPIOs before exiting
    print("Bye!")
    sys.exit()

    # Disable GPIO warnings
GPIO.setwarnings(False)

# Initialize HX711
hx = HX711(5, 6)

# Set the reading format to MSB (depends on your setup)
hx.set_reading_format("MSB", "MSB")

# Function to get a stable average weight by taking multiple readings
def get_average_weight(times=15, delay=0.1):
    """Get average of multiple readings to stabilize the weight measurement."""
    readings = []
    for _ in range(times):
        reading = hx.get_weight(5)  # Get a single reading
        readings.append(reading)
        time.sleep(delay)  # Small delay between readings
    average_weight = sum(readings) / len(readings)
    # Return only positive values
    return max(0, average_weight)

# Function to reset calibration with a known weight
def reset_calibration():
    print("Resetting calibration with a known weight...")

    # Step 1: Tare the scale to set the offset
    hx.tare()  # This sets the current ADC reading at 0g to offset
    print("Scale tared successfully. Offset set to current reading.")

    # Step 2: Prompt the user to place a known weight for calibration
    while True:
        known_weight = float(input("Place a known weight on the scale (e.g., 5kg) and enter its value in grams: "))
        if known_weight > 0:
            break
        else:
            print("Weight must be greater than zero. Please enter a valid weight.")

    print(f"Place the {known_weight}g weight on the scale and wait...")
    time.sleep(3)  # Wait for the weight to settle

    # Step 3: Get an average ADC reading with the known weight on the scale
    raw_value = get_average_weight(times=15, delay=0.1) - hx.get_offset()
    print(f"Calibrated ADC value for {known_weight}g weight (offset subtracted): {raw_value}")

    # Step 4: Calculate the reference unit
    reference_unit = raw_value / known_weight  # Scale factor per gram
    print(f"Calibration reset complete. New reference unit: {reference_unit}")

    # Set the reference unit for HX711
    hx.set_reference_unit(reference_unit)

    # Save the new calibration data to a file
    calibration_data = {
        "reference_unit": reference_unit,
        "calibration_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open("calibration_data.json", "w") as f:
        json.dump(calibration_data, f, indent=4)
    print("New calibration data saved to calibration_data.json")

    return reference_unit

# Load the reference unit from a JSON file (if it exists)
def load_reference_unit():
    try:
        with open("/home/xm23917/Desktop/weight/hx711py/calibration_data.json", "r") as f:
            calibration_data = json.load(f)
        reference_unit = calibration_data["reference_unit"]
        print(f"Loaded reference unit from file: {reference_unit}")
        hx.set_reference_unit(reference_unit)
    except (FileNotFoundError, KeyError) as e:
        print("No valid calibration data found. Starting calibration...")
        reference_unit = reset_calibration()

    return reference_unit

# Function to initialize the scale (tare it)
def initialize_scale():
    print("Taring the scale...")
    hx.reset()
    hx.tare()  # Set the offset to zero# Main function
def main():
    load_reference_unit()
    initialize_scale()  # Set new zero reading at start
    print("Scale ready. Starting real-time GUI with auto-capture on stabilization...")
    

if __name__ == "__main__":
    main()


# Main loop to read weight values
def main():
    # Load the reference unit from a JSON file or reset calibration if not found
    reference_unit = load_reference_unit()

    print("Make sure the scale is empty.")

    # Initialize the scale
    initialize_scale()

    print("Scale initialized. Add weight now...")

    last_weight = 0  # Track the last known weight

    try:
        while True:
            # Get a stable average weight
            val = get_average_weight(times=5, delay=0.1)

            # Only show positive weight values and check for weight changes
            if val > 0:
                last_weight = val  # Update last known weight
                print(f"Weight: {val:.2f} grams")
            else:
                # Weight is now zero (item removed), show 0 only if last_weight was non-zero
                if last_weight > 0:
                    print("Weight: 0.00 grams")
                last_weight = 0  # Reset the last known weight

            # Power down/up the HX711 to prevent noise and save power
            hx.power_down()
            hx.power_up()
            time.sleep(3)  # Delay between readings

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()

# Run the main function
if __name__ == "__main__":
    main()
