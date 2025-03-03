import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials (Replace with your Firebase key filename)
cred = credentials.Certificate("firebase-key.json")
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
        city, state = town.split(", ")  # Split "Greenport, NY" into "Greenport" and "NY"
        url = f"https://api.rentcast.io/v1/properties?city={city}&state={state}&limit=50"
        headers = {"X-Api-Key": API_KEY, "Accept": "application/json"}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"📡 API Response for {town}: {json.dumps(data, indent=2)}")

            if isinstance(data, list):  
                properties.extend(data)  # If API returns a list, append directly
            elif isinstance(data, dict) and "properties" in data:
                properties.extend(data["properties"])  # If it's a dictionary, extract "properties"
            else:
                print(f"⚠️ Unexpected response format for {town}: {data}")

        else:
            print(f"❌ Error fetching data for {town}: {response.json()}")

    print(f"🏡 Total properties fetched: {len(properties)}")
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

