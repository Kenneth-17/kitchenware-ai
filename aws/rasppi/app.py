# app.py
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
from openai import OpenAI
import requests
import time
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import json

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CameraS3Uploader:
    def __init__(self):
        self.bucket_name: str = os.getenv('S3_BUCKET_NAME', '')
        self.aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client with custom endpoint if provided
        s3_endpoint = os.getenv('S3_ENDPOINT_URL')
        s3_config = {
            'region_name': self.aws_region
        }
        if s3_endpoint:
            s3_config['endpoint_url'] = s3_endpoint
        
        self.s3_client = boto3.client('s3', **s3_config)
        
        # Initialize camera
        self.picam2 = Picamera2()
        self.camera_config = self.picam2.create_still_configuration(
            main={"size": (1920, 1080)},
            lores={"size": (640, 480)},
            display="lores"
        )
        self.picam2.configure(self.camera_config)

    def capture_image(self) -> str:
        """Capture image from Raspberry Pi camera v3"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"/tmp/image_{timestamp}.jpg"

            self.picam2.start()
            # Wait for auto exposure and white balance
            time.sleep(2)
            
            # Capture with metadata
            metadata = {
                "Created": datetime.now().isoformat(),
                "CameraModel": "Raspberry Pi Camera v3"
            }
            self.picam2.capture_file(local_filename, encode_metadata=metadata)
            self.picam2.stop()

            logger.info(f"Image captured and saved as {local_filename}")
            return local_filename

        except Exception as e:
            logger.error(f"Error capturing image: {e}", exc_info=True)
            raise

    def upload_to_s3(self, local_filename: str) -> str:
        """Upload image to S3"""
        try:
            object_key = f"images/{datetime.now().strftime('%Y/%m/%d')}/{os.path.basename(local_filename)}"
            
            # Upload with metadata and proper content type
            with open(local_filename, 'rb') as file:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_key,
                    ExtraArgs={
                        'ContentType': 'image/jpeg',
                        'Metadata': {
                            'captured-date': datetime.now().isoformat()
                        }
                    }
                )
            logger.info(f"Image uploaded to S3: {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}", exc_info=True)
            raise

    def generate_url(self, object_key: str, expiration: int = 3600) -> str:
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
            logger.error(f"Error generating presigned URL: {e}", exc_info=True)
            raise

    def cleanup(self, local_filename: str) -> None:
        """Remove local image file"""
        try:
            if os.path.exists(local_filename):
                os.remove(local_filename)
                logger.info(f"Local file removed: {local_filename}")
        except Exception as e:
            logger.error(f"Error removing local file: {e}", exc_info=True)


class NutritionAnalyzer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.nutritionix_app_id = os.getenv('NUTRITIONIX_APP_ID')
        self.nutritionix_api_key = os.getenv('NUTRITIONIX_API_KEY')
        self.nutritionix_api_url = "https://trackapi.nutritionix.com/v2/natural/nutrients"

    async def analyze_image(self, img_url: str) -> str:
        """Analyze image using OpenAI API"""
        try:
            response = await self.openai_client.chat.completions.create(
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
            logger.error(f"Error analyzing image with OpenAI: {e}", exc_info=True)
            raise

    def get_nutrition_info(self, food_name: str, serving_grams: float) -> Dict[str, Any]:
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
            logger.error(f"Error getting nutrition info: {e}", exc_info=True)
            raise


async def main() -> None:
    local_filename: Optional[str] = None
    uploader: Optional[CameraS3Uploader] = None
    
    try:
        uploader = CameraS3Uploader()
        analyzer = NutritionAnalyzer()
        
        # Test S3 permissions
        try:
            uploader.s3_client.head_bucket(Bucket=uploader.bucket_name)
            logger.info(f"Successfully connected to bucket: {uploader.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 bucket error: {error_code}")
            raise

        # Capture and upload image
        local_filename = uploader.capture_image()
        object_key = uploader.upload_to_s3(local_filename)
        img_url = uploader.generate_url(object_key)
        
        # Analyze image and get food name
        food_name = await analyzer.analyze_image(img_url)
        print(f"Detected food: {food_name}")
        
        # Get serving size from user
        while True:
            try:
                serving_input = input("Enter the serving size in grams: ")
                serving_grams = float(serving_input)
                if serving_grams <= 0:
                    raise ValueError("Serving size must be positive")
                break
            except ValueError as e:
                print(f"Invalid input: {e}. Please enter a positive number.")
        
        # Get nutrition information
        nutrition_data = analyzer.get_nutrition_info(food_name, serving_grams)
        
        # Display results
        for food in nutrition_data['foods']:
            print("\nNutrition Information:")
            print(f"Food Name: {food['food_name']}")
            print(f"Serving Weight: {food['serving_weight_grams']:.1f} grams")
            print(f"Calories: {food['nf_calories']:.1f} kcal")
            print(f"Total Fat: {food['nf_total_fat']:.1f} g")
            print(f"Saturated Fat: {food['nf_saturated_fat']:.1f} g")
            print(f"Cholesterol: {food['nf_cholesterol']:.1f} mg")
            print(f"Sodium: {food['nf_sodium']:.1f} mg")
            print(f"Total Carbohydrates: {food['nf_total_carbohydrate']:.1f} g")
            print(f"Dietary Fiber: {food['nf_dietary_fiber']:.1f} g")
            print(f"Sugars: {food['nf_sugars']:.1f} g")
            print(f"Protein: {food['nf_protein']:.1f} g")
            
            # Save results to a JSON file
            result_filename = f"/tmp/nutrition_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_filename, 'w') as f:
                json.dump(food, f, indent=2)
            print(f"\nDetailed results saved to: {result_filename}")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if local_filename and uploader:
            uploader.cleanup(local_filename)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())