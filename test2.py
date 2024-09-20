import requests
import sqlite3
import pandas as pd
from openai import OpenAI

def get_food_name_from_image(client, img_url):
    """
    Uses OpenAI's API to identify the food item in the image.
    """
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
    return response.choices[0].message.content.strip()

def get_nutritional_info(food_name, serving_grams, api_url, app_id, api_key):
    """
    Fetches nutritional information from the Nutritionix API.
    """
    # Create the query string
    query = f"{serving_grams} grams of {food_name}"

    # Headers required by the API
    headers = {
        "x-app-id": app_id,
        "x-app-key": api_key,
        "Content-Type": "application/json"
    }

    # The data to send in the POST request
    data = {
        "query": query,
        "timezone": "US/Eastern"
    }

    # Make the POST request
    response = requests.post(api_url, headers=headers, json=data)

    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def initialize_database():
    """
    Initializes the SQLite database and creates tables if they don't exist.
    """
    conn = sqlite3.connect('food_log.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')

    # Create food_entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            food_name TEXT,
            serving_weight_grams REAL,
            calories REAL,
            total_fat REAL,
            carbohydrates REAL,
            protein REAL,
            entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create user_totals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_totals (
            user_id INTEGER PRIMARY KEY,
            total_calories REAL DEFAULT 0,
            total_fat REAL DEFAULT 0,
            total_carbohydrates REAL DEFAULT 0,
            total_protein REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    return conn

def get_or_create_user(conn, username):
    """
    Retrieves the user ID for the given username, creating a new user if necessary.
    """
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
    else:
        cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
        conn.commit()
        user_id = cursor.lastrowid
        # Initialize user totals
        initialize_user_totals(conn, user_id)
    return user_id

def initialize_user_totals(conn, user_id):
    """
    Initializes the totals for a new user.
    """
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_totals (user_id) VALUES (?)
    ''', (user_id,))
    conn.commit()

def update_user_totals(conn, user_id, food_data):
    """
    Updates the user's total nutritional values.
    """
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_totals
        SET total_calories = total_calories + ?,
            total_fat = total_fat + ?,
            total_carbohydrates = total_carbohydrates + ?,
            total_protein = total_protein + ?
        WHERE user_id = ?
    ''', (
        food_data['nf_calories'],
        food_data['nf_total_fat'],
        food_data['nf_total_carbohydrate'],
        food_data['nf_protein'],
        user_id
    ))
    conn.commit()

def get_user_totals(conn, user_id):
    """
    Retrieves the user's total nutritional values.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_calories, total_fat, total_carbohydrates, total_protein
        FROM user_totals
        WHERE user_id = ?
    ''', (user_id,))
    return cursor.fetchone()

def save_food_entry(conn, user_id, food_data):
    """
    Saves the food entry into the database.
    """
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO food_entries (
            user_id, food_name, serving_weight_grams, calories,
            total_fat, carbohydrates, protein
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        food_data['food_name'],
        food_data['serving_weight_grams'],
        food_data['nf_calories'],
        food_data['nf_total_fat'],
        food_data['nf_total_carbohydrate'],
        food_data['nf_protein']
    ))
    conn.commit()

def display_user_food_entries(conn, user_id):
    """
    Displays all food entries for the given user.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT food_name, serving_weight_grams, calories, total_fat,
               carbohydrates, protein, entry_date
        FROM food_entries
        WHERE user_id = ?
        ORDER BY entry_date DESC
    ''', (user_id,))
    entries = cursor.fetchall()
    print("\nYour Food Log:")
    print("-" * 50)
    for entry in entries:
        print(f"Date: {entry[6]}")
        print(f"Food Name: {entry[0]}")
        print(f"Serving Weight: {entry[1]} grams")
        print(f"Calories: {entry[2]} kcal")
        print(f"Total Fat: {entry[3]} g")
        print(f"Carbohydrates: {entry[4]} g")
        print(f"Protein: {entry[5]} g")
        print("-" * 50)
    return entries  # Return entries for Excel export

def display_user_totals(conn, user_id):
    """
    Displays the total nutritional values for the user.
    """
    totals = get_user_totals(conn, user_id)
    if totals:
        print("\nYour Total Nutritional Intake:")
        print("-" * 50)
        print(f"Total Calories: {totals[0]} kcal")
        print(f"Total Fat: {totals[1]} g")
        print(f"Total Carbohydrates: {totals[2]} g")
        print(f"Total Protein: {totals[3]} g")
        print("-" * 50)
    else:
        print("No totals available.")
    return totals  # Return totals for Excel export

def export_to_excel(food_entries, totals, username):
    """
    Exports the user's food entries and totals to an Excel file.
    """
    # Convert food entries to a pandas DataFrame
    food_df = pd.DataFrame(food_entries, columns=[
        'Food Name', 'Serving Weight (g)', 'Calories (kcal)',
        'Total Fat (g)', 'Carbohydrates (g)', 'Protein (g)', 'Date'
    ])

    # Convert totals to a DataFrame
    totals_df = pd.DataFrame([totals], columns=[
        'Total Calories (kcal)', 'Total Fat (g)', 'Total Carbohydrates (g)', 'Total Protein (g)'
    ])

    # Create a Pandas Excel writer using XlsxWriter as the engine
    excel_file = f"{username}_food_log.xlsx"
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        food_df.to_excel(writer, sheet_name='Food Entries', index=False)
        totals_df.to_excel(writer, sheet_name='Totals', index=False)

    print(f"\nData exported to {excel_file}")

def main():
    # OpenAI API key (replace with your own API key)
    openai_api_key = 'sk-Qx1xcQJlq6ZcIeJisyyzfuhSB8WFAkWt77PDjm9IbTT3BlbkFJbWQvNZHUP9VvA9Z1TAxo-R2b2gdUP1Jgwr8SKn5joA'

    # Initialize the OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # Initialize the database
    conn = initialize_database()

    # User Authentication (simple username-based login)
    username = input("Enter your username: ").strip()
    user_id = get_or_create_user(conn, username)

    # Ask the user for the image URL
    img_url = input("Enter the image URL: ").strip()

    # Get the food name from the image
    food_name = get_food_name_from_image(client, img_url)
    print(f"\nIdentified Food: {food_name}")

    # Ask the user for the serving size in grams
    serving_grams = input("Enter the serving size in grams: ")

    # Validate the serving size input
    try:
        serving_grams = float(serving_grams)
    except ValueError:
        print("Please enter a valid number for the serving size.")
        return

    # Nutritionix API credentials (replace with your own App ID and API Key)
    API_URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"
    APP_ID = "94615eef"
    API_KEY = "5e7a357053959ca39c053ba924460cc9"

    # Get the nutritional information
    nutrition_data = get_nutritional_info(food_name, serving_grams, API_URL, APP_ID, API_KEY)

    if nutrition_data:
        # Print and save the results
        for food in nutrition_data['foods']:
            print(f"\nFood Name: {food['food_name']}")
            print(f"Serving Weight: {food['serving_weight_grams']} grams")
            print(f"Calories: {food['nf_calories']} kcal")
            print(f"Total Fat: {food['nf_total_fat']} g")
            print(f"Carbohydrates: {food['nf_total_carbohydrate']} g")
            print(f"Protein: {food['nf_protein']} g")
            print("-" * 30)

            # Save the food entry into the database
            save_food_entry(conn, user_id, food)

            # Update the user's total nutritional values
            update_user_totals(conn, user_id, food)

        # Display all food entries for the user
        food_entries = display_user_food_entries(conn, user_id)

        # Display the user's total nutritional intake
        totals = display_user_totals(conn, user_id)

        # Export data to Excel
        export_to_excel(food_entries, totals, username)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
