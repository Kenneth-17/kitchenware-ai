import RPi.GPIO as GPIO
from hx711 import HX711
import time

# Disable GPIO warnings
GPIO.setwarnings(False)

# Define GPIO pins connected to HX711
DT_PIN = 5  # GPIO5 (Physical Pin 29)
SCK_PIN = 6  # GPIO6 (Physical Pin 31)

# Function to simulate LED indicator with console output
def led_on():
    print("[LED ON]")  # Simulate LED ON

def led_off():
    print("[LED OFF]")  # Simulate LED OFF

# Function to "blink" using console output
def blink_led(times, interval=0.5):
    for _ in range(times):
        led_on()
        time.sleep(interval)
        led_off()
        time.sleep(interval)

# Initialize HX711
def initialize_hx711(dt_pin, sck_pin):
    print("[DEBUG] Initializing HX711...")
    hx = HX711(dt_pin, sck_pin)
    print("[DEBUG] HX711 successfully initialized")
    return hx

# Set the reference unit for calibration
def setup_hx711(hx):
    print("[DEBUG] Setting reading format...")
    hx.set_reading_format("MSB", "MSB")  # Set the bit order
    print("[DEBUG] Reading format set successfully")

    try:
        known_weight = float(input("Enter the weight of a known mass (in grams) to calibrate: "))
        print("Place the known weight on the scale...")
        time.sleep(5)  # Wait for the user to place the weight

        reading = hx.get_weight(5)  # Average over 5 readings
        print(f"[DEBUG] Reading from load cell with known weight: {reading:.2f}")
        if reading != 0:
            calibration_factor = reading / known_weight
            hx.set_reference_unit(calibration_factor)
            print(f"[DEBUG] Calibration factor set to: {calibration_factor:.2f}")
        else:
            print("[ERROR] Reading is zero, check the load cell.")
    except ValueError:
        print("[ERROR] Invalid input. Please enter a numeric value.")

# Reset HX711 and tare the load cell
def reset_and_tare_hx711(hx):
    print("[DEBUG] Resetting HX711...")
    hx.reset()  # Reset the HX711
    print("[DEBUG] HX711 reset successfully")

    print("[DEBUG] Taring the load cell to set the zero point...")
    blink_led(3, 0.2)  # Blink 3 times to indicate taring process
    hx.tare()  # Tare to set the zero point
    time.sleep(2)  # Allow some time for the tare to stabilize
    print("[DEBUG] Load cell tared successfully")

# Measure weight
def measure_weight(hx):
    try:
        weight = hx.get_weight(5)  # Average over 5 readings
        if weight is not None:
            print(f"[DEBUG] Raw Weight Reading: {weight:.2f} g")
            calibrated_weight = weight  # Already calibrated
            print(f"[DEBUG] Calibrated Weight: {calibrated_weight:.2f} g")
        else:
            print("[ERROR] Failed to get weight. Check wiring.")
    except Exception as e:
        print(f"[ERROR] Exception occurred while getting weight: {e}")

# Main execution
if __name__ == "__main__":
    try:
        hx = initialize_hx711(DT_PIN, SCK_PIN)
        setup_hx711(hx)
        reset_and_tare_hx711(hx)

        print("[DEBUG] Taring complete. Starting weight measurement...")
        blink_led(2, 0.5)  # Blink 2 times to indicate the start of measurement

        while True:
            # Blink to show the program is running
            led_on()
            time.sleep(0.1)
            led_off()
            time.sleep(0.1)

            # Read weight from the strain gauge bridge
            print("[DEBUG] Reading weight from load cell...")
            measure_weight(hx)

            time.sleep(1)  # Delay to avoid rapid prints

    except KeyboardInterrupt:
        print("\n[DEBUG] Exiting...")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
    finally:
        GPIO.cleanup()  # Clean up the GPIO pins to avoid warnings
        led_off()  # "Turn off" LED on exit
        print("[DEBUG] Cleanup complete")
