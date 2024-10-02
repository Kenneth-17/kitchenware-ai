from picamera2 import Picamera2
import boto3
import os
from datetime import datetime
import logging
import requests
import time
from openai import OpenAI
import json

# Configuration
AWS_ACCESS_KEY_ID = "AKIAVY2PG2WSM6DGORVH"
AWS_SECRET_ACCESS_KEY = "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"
S3_BUCKET_NAME = "kitchencounter"
AWS_REGION = "us-east-1"
OPENAI_API_KEY = "sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA"
NUTRITIONIX_APP_ID = "94615eef"
NUTRITIONIX_API_KEY = "5e7a357053959ca39c053ba924460cc9"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraS3Uploader:
    def __init__(self):
        self.bucket_name = S3_BUCKET_NAME
        self.s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        self.picam2 = Picamera2()
        self.camera_config = self.picam2.create_still_configuration(
            main={"size": (1920, 1080)},
            lores={"size": (640, 480)},
            display="lores"
        )
        self.picam2.configure(self.camera_config)

    def capture_image(self):
        """Capture image from Raspberry Pi camera"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"image_{timestamp}.jpg"

            self.picam2.start()
            time.sleep(2)  # Wait for camera to warm up
            self.picam2.capture_file(local_filename)
            self.picam2.stop()

            logger.info(f"Image captured: {local_filename}")
            return local_filename
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            raise

    def upload_to_s3(self, local_filename):
        """Upload image to S3"""
        try:
            object_key = f"images/{datetime.now().strftime('%Y/%m/%d')}/{local_filename}"
            
            with open(local_filename, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
            logger.info(f"Image uploaded to S3: {object_key}")
            return object_key
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
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
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

class NutritionAnalyzer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.nutritionix_api_url = "https://trackapi.nutritionix.com/v2/natural/nutrients"

    def analyze_image(self, img_url):
        """Analyze image using OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What food item is shown in this image? Please provide just the name."},
                            {"type": "image_url", "image_url": {"url": img_url}}
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error analyzing image with OpenAI: {e}")
            raise

    def get_nutrition_info(self, food_name, serving_grams):
        """Get nutrition information from Nutritionix API"""
        try:
            headers = {
                "x-app-id": NUTRITIONIX_APP_ID,
                "x-app-key": NUTRITIONIX_API_KEY,
                "Content-Type": "application/json"
            }
            
            data = {
                "query": f"{serving_grams} grams of {food_name}",
                "timezone": "US/Eastern"
            }
            
            response = requests.post(self.nutritionix_api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting nutrition info: {e}")
            raise

def cleanup(filename):
    """Remove local image file"""
    try:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Cleaned up local file: {filename}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def main():
    local_filename = None
    try:
        # Initialize classes
        camera_uploader = CameraS3Uploader()
        nutrition_analyzer = NutritionAnalyzer()

        # Capture and upload image
        local_filename = camera_uploader.capture_image()
        object_key = camera_uploader.upload_to_s3(local_filename)
        img_url = camera_uploader.generate_url(object_key)
        
        # Analyze image
        print("Analyzing image...")
        food_name = nutrition_analyzer.analyze_image(img_url)
        print(f"Detected food: {food_name}")
        
        # Get serving size from user
        while True:
            try:
                serving_input = input("Enter the serving size in grams: ")
                serving_grams = float(serving_input)
                if serving_grams <= 0:
                    raise ValueError
                break
            except ValueError:
                print("Please enter a valid positive number.")
        
        # Get and display nutrition information
        print("Fetching nutrition information...")
        nutrition_data = nutrition_analyzer.get_nutrition_info(food_name, serving_grams)
        
        # Save and display results
        for food in nutrition_data['foods']:
            print("\nNutrition Information:")
            print(f"Food Name: {food['food_name']}")
            print(f"Serving Weight: {food['serving_weight_grams']:.1f} g")
            print(f"Calories: {food['nf_calories']:.1f} kcal")
            print(f"Total Fat: {food['nf_total_fat']:.1f} g")
            print(f"Saturated Fat: {food['nf_saturated_fat']:.1f} g")
            print(f"Cholesterol: {food['nf_cholesterol']:.1f} mg")
            print(f"Sodium: {food['nf_sodium']:.1f} mg")
            print(f"Total Carbohydrates: {food['nf_total_carbohydrate']:.1f} g")
            print(f"Dietary Fiber: {food['nf_dietary_fiber']:.1f} g")
            print(f"Sugars: {food['nf_sugars']:.1f} g")
            print(f"Protein: {food['nf_protein']:.1f} g")
            
            # Save results to JSON
            result_filename = f"nutrition_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_filename, 'w') as f:
                json.dump(food, f, indent=2)
            print(f"\nDetailed results saved to: {result_filename}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if local_filename:
            cleanup(local_filename)

if __name__ == "__main__":
    main()