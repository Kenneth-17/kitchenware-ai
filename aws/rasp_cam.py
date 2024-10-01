from picamera2 import Picamera2
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
from openai import OpenAI
import requests
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraS3Uploader:
    def __init__(self, bucket_name, aws_region='us-east-1'):
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        self.picam2 = Picamera2()

    def capture_image(self):
        """Capture image from Raspberry Pi camera v3"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"image_{timestamp}.jpg"

            # Configure and start the camera
            config = self.picam2.create_still_configuration()
            self.picam2.configure(config)
            self.picam2.start()
            
            # Wait for auto exposure and auto white balance to settle
            time.sleep(2)
            
            # Capture the image
            self.picam2.capture_file(local_filename)
            
            # Stop the camera
            self.picam2.stop()

            logger.info(f"Image captured and saved as {local_filename}")
            return local_filename

        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
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
            if os.path.exists(local_filename):
                os.remove(local_filename)
                logger.info(f"Local file removed: {local_filename}")
        except Exception as e:
            logger.error(f"Error removing local file: {str(e)}")

class NutritionAnalyzer:
    def __init__(self, openai_api_key, nutritionix_app_id, nutritionix_api_key):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.nutritionix_app_id = nutritionix_app_id
        self.nutritionix_api_key = nutritionix_api_key
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
                            {"type": "text", "text": "What's in this image? Please provide just the food name."},
                            {"type": "image_url", "image_url": {"url": img_url}}
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error analyzing image with OpenAI: {str(e)}")
            raise

    def get_nutrition_info(self, food_name, serving_grams):
        """Get nutrition information from Nutritionix API"""
        try:
            headers = {
                "x-app-id": self.nutritionix_app_id,
                "x-app-key": self.nutritionix_api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "query": f"{serving_grams} grams of {food_name}",
                "timezone": "US/Eastern"
            }
            
            response = requests.post(self.nutritionix_api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting nutrition info: {str(e)}")
            raise

def main():
    # Configuration
    CONFIG = {
        'BUCKET_NAME': "kitchencounter",
        'AWS_REGION': "us-east-1",
        'OPENAI_API_KEY': 'your-openai-api-key',
        'NUTRITIONIX_APP_ID': "94615eef",
        'NUTRITIONIX_API_KEY': "5e7a357053959ca39c053ba924460cc9"
    }

    try:
        uploader = CameraS3Uploader(CONFIG['BUCKET_NAME'], CONFIG['AWS_REGION'])
        analyzer = NutritionAnalyzer(
            CONFIG['OPENAI_API_KEY'],
            CONFIG['NUTRITIONIX_APP_ID'],
            CONFIG['NUTRITIONIX_API_KEY']
        )
        
        # Test S3 permissions
        try:
            uploader.s3_client.head_bucket(Bucket=CONFIG['BUCKET_NAME'])
            logger.info(f"Successfully connected to bucket: {CONFIG['BUCKET_NAME']}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 bucket error: {error_code}")
            raise

        # Capture and upload image
        local_filename = uploader.capture_image()
        object_key = uploader.upload_to_s3(local_filename)
        img_url = uploader.generate_url(object_key)
        
        # Analyze image and get food name
        food_name = analyzer.analyze_image(img_url)
        print(f"Detected food: {food_name}")
        
        # Get serving size from user
        serving_grams = input("Enter the serving size in grams: ")
        
        # Get nutrition information
        nutrition_data = analyzer.get_nutrition_info(food_name, serving_grams)
        
        # Display results
        for food in nutrition_data['foods']:
            print(f"\nNutrition Information:")
            print(f"Food Name: {food['food_name']}")
            print(f"Serving Weight: {food['serving_weight_grams']} grams")
            print(f"Calories: {food['nf_calories']:.1f} kcal")
            print(f"Total Fat: {food['nf_total_fat']:.1f} g")
            print(f"Carbohydrates: {food['nf_total_carbohydrate']:.1f} g")
            print(f"Protein: {food['nf_protein']:.1f} g")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        if 'local_filename' in locals() and 'uploader' in locals():
            uploader.cleanup(local_filename)

if __name__ == "__main__":
    main()