import cv2
import mediapipe as mp
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

# Initialize camera
cap = cv2.VideoCapture(1)

# Variables for timing
program_start_time = time.time()
STARTUP_DELAY = 5  # seconds before starting hand detection

# Variables for hand detection and capture
hands_detected = False  # New flag to track if hands have been detected
hand_removed = False
countdown_started = False
countdown_start_time = 0
COUNTDOWN_DURATION = 3  # seconds

while True:
    success, img = cap.read()
    if not success:
        print("Failed to grab frame")
        break

    current_time = time.time()
    elapsed_since_start = current_time - program_start_time
    
    # Check if we're still in the startup delay period
    if elapsed_since_start < STARTUP_DELAY:
        # Display countdown to hand detection start
        remaining_startup = int(STARTUP_DELAY - elapsed_since_start)
        cv2.putText(img, f"Starting in: {remaining_startup}", (10, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow("Hand Detection", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue  # Skip hand detection during startup delay

    # Convert BGR image to RGB
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Process the image and detect hands
    results = hands.process(rgb_img)
    
    # Check for hands
    if results.multi_hand_landmarks:
        hands_detected = True  # We've seen hands
        hand_removed = False
        countdown_started = False
        
        # Draw hand landmarks
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        # Display "Hands detected" message
        cv2.putText(img, "Hands detected", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        if hands_detected and not hand_removed:  # Only start countdown if we've seen hands before
            hand_removed = True
            countdown_start_time = time.time()
            countdown_started = True
    
    # Handle countdown and capture
    if countdown_started:
        elapsed_time = time.time() - countdown_start_time
        if elapsed_time < COUNTDOWN_DURATION:
            # Display countdown
            remaining = int(COUNTDOWN_DURATION - elapsed_time)
            cv2.putText(img, f"Capturing in: {remaining}", (10, 70), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif elapsed_time >= COUNTDOWN_DURATION:
            # Capture image
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"captured_{timestamp}.jpg"
            cv2.imwrite(filename, img)
            print(f"Image captured: {filename}")
            countdown_started = False
            hands_detected = False  # Reset for the next detection cycle

    # Show that hand detection is active
    cv2.putText(img, "Hand detection active", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    if not hands_detected:
        cv2.putText(img, "Waiting for hands...", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    
    # Display the image
    cv2.imshow("Hand Detection", img)
    
    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()