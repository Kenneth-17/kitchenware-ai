import cv2
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
import requests
import mediapipe as mp
import time
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HandDetectionCameraS3Uploader:
    def __init__(self, bucket_name, aws_region='us-east-1'):
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_draw = mp.solutions.drawing_utils

    def capture_image_with_hand_detection(self):
        """Capture image using hand detection logic"""
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            raise Exception("Could not open camera")

        program_start_time = time.time()
        STARTUP_DELAY = 5
        hands_detected = False
        hand_removed = False
        countdown_started = False
        countdown_start_time = 0
        COUNTDOWN_DURATION = 3

        local_filename = None

        while True:
            success, img = cap.read()
            if not success:
                logger.error("Failed to grab frame")
                break

            current_time = time.time()
            elapsed_since_start = current_time - program_start_time

            if elapsed_since_start < STARTUP_DELAY:
                remaining_startup = int(STARTUP_DELAY - elapsed_since_start)
                cv2.putText(img, f"Starting in: {remaining_startup}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_img)

                if results.multi_hand_landmarks:
                    hands_detected = True
                    hand_removed = False
                    countdown_started = False

                    for hand_landmarks in results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    cv2.putText(img, "Hands detected", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    if hands_detected and not hand_removed:
                        hand_removed = True
                        countdown_start_time = time.time()
                        countdown_started = True

                if countdown_started:
                    elapsed_time = time.time() - countdown_start_time
                    if elapsed_time < COUNTDOWN_DURATION:
                        remaining = int(COUNTDOWN_DURATION - elapsed_time)
                        cv2.putText(img, f"Capturing in: {remaining}", (10, 70),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    elif elapsed_time >= COUNTDOWN_DURATION:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        local_filename = f"image_{timestamp}.jpg"
                        cv2.imwrite(local_filename, img)
                        logger.info(f"Image captured and saved as {local_filename}")
                        break

                cv2.putText(img, "Hand detection active", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if not hands_detected:
                    cv2.putText(img, "Waiting for hands...", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            cv2.imshow("Hand Detection", img)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        
        if local_filename and os.path.exists(local_filename):
            return local_filename
        else:
            raise Exception("Failed to capture image")

    def upload_to_s3(self, local_filename):
        """Upload image to S3"""
        try:
            object_key = f"images/{datetime.now().strftime('%Y/%m/%d')}/{local_filename}"
            
            with open(local_filename, 'rb') as file:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=file
                )
            logger.info(f"Image uploaded to S3: {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise

    def generate_url(self, object_key, expiration=3600):
        """Generate presigned URL for the uploaded image"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

    def cleanup(self, local_filename):
        """Remove local image file"""
        try:
            os.remove(local_filename)
            logger.info(f"Local file removed: {local_filename}")
        except Exception as e:
            logger.error(f"Error removing local file: {str(e)}")

def call_openai_api(image_url, api_key):
    """Make a direct API call to OpenAI without using the client library"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What food item is in this image? Also, what weight (in grams) is shown on the scale in the image? Please respond in the format: 'Food: [food name], Weight: [weight in grams]g'"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 401:
            logger.error("Authentication error: Please check your API key")
            raise Exception("OpenAI API authentication failed")
        
        response.raise_for_status()
        
        try:
            return response.json()["choices"][0]["message"]["content"]
        except KeyError as e:
            logger.error(f"Unexpected API response structure: {response.text}")
            raise Exception("Unexpected API response structure") from e
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        raise

def main():
    # Configuration
    BUCKET_NAME = "kitchencounter"
    AWS_REGION = "us-east-1"
    OPENAI_API_KEY = 'sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA'  # Replace with your actual OpenAI API key
    NUTRITIONIX_APP_ID = "94615eef"
    NUTRITIONIX_API_KEY = "5e7a357053959ca39c053ba924460cc9"

    try:
        uploader = HandDetectionCameraS3Uploader(BUCKET_NAME, AWS_REGION)
        
        # Test S3 permissions
        try:
            uploader.s3_client.head_bucket(Bucket=BUCKET_NAME)
            logger.info(f"Successfully connected to bucket: {BUCKET_NAME}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '403':
                logger.error(f"Permission denied to access bucket: {BUCKET_NAME}")
            elif error_code == '404':
                logger.error(f"Bucket not found: {BUCKET_NAME}")
            raise

        local_filename = uploader.capture_image_with_hand_detection()
        object_key = uploader.upload_to_s3(local_filename)
        img_url = uploader.generate_url(object_key)
        
        # Debug logging
        logger.info(f"Generated pre-signed URL: {img_url}")
        
        # OpenAI processing with workaround
        try:
            logger.info("Calling OpenAI API...")
            ai_response = call_openai_api(img_url, OPENAI_API_KEY)
            logger.info(f"OpenAI response: {ai_response}")
            
            # Parse the AI response
            food_name = ai_response.split(',')[0].split(':')[1].strip()
            weight = ai_response.split(',')[1].split(':')[1].strip()
            weight = weight[:-1] if weight.endswith('g') else weight  # Remove 'g' if present
            
            logger.info(f"Identified food: {food_name}")
            logger.info(f"Detected weight: {weight} grams")
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {str(e)}")
            raise

        # Nutritionix API processing
        NUTRITIONIX_API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"

        query = f"{weight} grams of {food_name}"

        headers = {
            "x-app-id": NUTRITIONIX_APP_ID,
            "x-app-key": NUTRITIONIX_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "query": query,
            "timezone": "US/Eastern"
        }

        nutritionix_response = requests.post(NUTRITIONIX_API_URL, headers=headers, json=data)

        if nutritionix_response.status_code == 200:
            result = nutritionix_response.json()
            for food in result['foods']:
                print(f"Food Name: {food['food_name']}")
                print(f"Serving Weight: {food['serving_weight_grams']} grams")
                print(f"Calories: {food['nf_calories']} kcal")
                print(f"Total Fat: {food['nf_total_fat']} g")
                print(f"Carbohydrates: {food['nf_total_carbohydrate']} g")
                print(f"Protein: {food['nf_protein']} g")
                print("-" * 30)
        else:
            print(f"Error: {nutritionix_response.status_code}")
            print(nutritionix_response.text)

        uploader.cleanup(local_filename)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if 'local_filename' in locals():
            try:
                os.remove(local_filename)
                logger.info(f"Cleaned up local file after error: {local_filename}")
            except:
                pass

if __name__ == "__main__":
    main()