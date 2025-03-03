import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials (Replace with your Firebase key filename)
cred = credentials.Certificate("your-firebase-key.json")  
firebase_admin.initialize_app(cred)
db = firestore.client()

# RentCast API Key
API_KEY = "36952abfe82240b2b29156c67e1426dd"  # Replace with your API Key

# List of towns we want to track
TOWNS = ["Greenport, NY", "Southold, NY", "East Hampton, NY"]

# Function to fetch property data
def fetch_property_data():
    properties = []
    for town in TOWNS:
        url = f"https://api.rentcast.io/v1/properties?city_state={town.replace(' ', '%20')}"
        headers = {"X-API-Key": API_KEY}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            properties.extend(data.get("properties", []))  # Extract property list
        else:
            print(f"Error fetching data for {town}: {response.json()}")

    return properties

# Function to update Firebase
def update_firebase(properties):
    for property in properties:
        address = property.get("address", "Unknown Address")
        if address == "Unknown Address":
            continue

        doc_ref = db.collection("properties").document(address.replace(" ", "_"))
        doc_ref.set(property)
        print(f"Updated Firebase with {address}")

# Fetch data and update Firebase
properties = fetch_property_data()
if properties:
    update_firebase(properties)
    print("✅ Data successfully updated in Firebase!")
else:
    print("❌ No properties found.")

