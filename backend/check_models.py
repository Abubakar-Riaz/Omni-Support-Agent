import requests
import dotenv
import os

dotenv.load_dotenv()

# Replace with your actual API key
API_KEY = os.getenv("GOOGLE_API_KEY")

# Endpoint to list models
url = "https://generativelanguage.googleapis.com/v1/models"

# Make the request
response = requests.get(url, params={"key": API_KEY})

if response.status_code == 200:
    models = response.json()
    print("Available models:")
    for model in models.get("models", []):
        print(f"- {model['name']}")
else:
    print("Error:", response.status_code, response.text)