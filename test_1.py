from openai import OpenAI
import requests

#open API cliient
client = OpenAI(api_key='sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA')

#image url
img_url = 'https://www.shutterstock.com/image-photo/raw-chicken-fillet-pieces-fresh-260nw-2044930682.jpg'


#query to send image with prompt to get food item
response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What’s in this image, just the food name?"},
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

#print(response.choices[0].message.content)

# Your Nutritionix API credentials
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
APP_ID = "94615eef"
API_KEY = "5e7a357053959ca39c053ba924460cc9"

# The food name (you can set this programmatically or obtain it from another part of your program)
food_name = response.choices[0].message.content  # Replace this with the food name variable from your earlier code

# Ask the user for the serving size in grams
serving_grams = input("Enter the serving size in grams: ")

# Create the query string with the serving size in grams
query = f"{serving_grams} grams of {food_name}"

# Headers required by the API
headers = {
    "x-app-id": APP_ID,
    "x-app-key": API_KEY,
    "Content-Type": "application/json"
}

# The data to send in the POST request
data = {
    "query": query,
    "timezone": "US/Eastern"
}

# Make the POST request
response = requests.post(API_URL, headers=headers, json=data)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    result = response.json()
    # Print the results
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