import cv2
import boto3
import os
from datetime import datetime
import logging
from botocore.exceptions import ClientError
from openai import OpenAI
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CameraS3Uploader:
    def __init__(self, bucket_name, aws_region='us-east-1'):
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.s3_client = boto3.client('s3', region_name=self.aws_region)

    def capture_image(self):
        """Capture image from camera"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise Exception("Could not open camera")

            ret, frame = cap.read()
            if not ret:
                raise Exception("Could not capture frame")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"image_{timestamp}.jpg"

            cv2.imwrite(local_filename, frame)
            logger.info(f"Image captured and saved as {local_filename}")

            cap.release()
            return local_filename

        except Exception as e:
            logger.error(f"Error capturing image: {str(e)}")
            raise

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

def main():
    # Configuration
    BUCKET_NAME = "kitchencounter"
    AWS_REGION = "us-east-1"

    try:
        uploader = CameraS3Uploader(BUCKET_NAME, AWS_REGION)
        
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

        local_filename = uploader.capture_image()
        object_key = uploader.upload_to_s3(local_filename)
        img_url = uploader.generate_url(object_key)
        
        # Your existing OpenAI and Nutritionix code starts here
        client = OpenAI(api_key='sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA')

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image, just the food name?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": img_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )

        API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
        APP_ID = "94615eef"
        API_KEY = "5e7a357053959ca39c053ba924460cc9"

        food_name = response.choices[0].message.content

        serving_grams = input("Enter the serving size in grams: ")

        query = f"{serving_grams} grams of {food_name}"

        headers = {
            "x-app-id": APP_ID,
            "x-app-key": API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "query": query,
            "timezone": "US/Eastern"
        }

        response = requests.post(API_URL, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            for food in result['foods']:
                print(f"Food Name: {food['food_name']}")
                print(f"Serving Weight: {food['serving_weight_grams']} grams")
                print(f"Calories: {food['nf_calories']} kcal")
                print(f"Total Fat: {food['nf_total_fat']} g")
                print(f"Carbohydrates: {food['nf_total_carbohydrate']} g")
                print(f"Protein: {food['nf_protein']} g")
                print("-" * 30)
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

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
    main()100