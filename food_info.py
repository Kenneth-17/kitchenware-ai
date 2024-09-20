import requests

# Your Nutritionix API credentials
API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
APP_ID = "94615eef"
API_KEY = "5e7a357053959ca39c053ba924460cc9"

# The food name (you can set this programmatically or obtain it from another part of your program)
food_name = "Broccoli"  # Replace this with the food name variable from your earlier code

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
