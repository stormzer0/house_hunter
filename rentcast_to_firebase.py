import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials (Replace with your Firebase key filename)
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials from GitHub Secret
firebase_key_path = "firebase-key.json"
with open(firebase_key_path, "w") as f:
    f.write(os.getenv("FIREBASE_KEY"))

cred = credentials.Certificate(firebase_key_path)

try:
    firebase_admin.initialize_app(cred)
    print("✅ Firebase successfully initialized.")
except ValueError:
    print("⚠️ Firebase already initialized.")

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
            print(f"📡 API Response for {town}: {json.dumps(data, indent=2)}")  # Debug: Print API response

            if isinstance(data, list) and len(data) > 0:  
                properties.extend(data)  # If API returns a list, append directly
            elif isinstance(data, dict) and "properties" in data and len(data["properties"]) > 0:
                properties.extend(data["properties"])  # If it's a dictionary, extract "properties"
            else:
                print(f"⚠️ Unexpected or empty response format for {town}: {data}")

        else:
            print(f"❌ API Error for {town}: {response.status_code}, Response: {response.json()}")

    print(f"🏡 Total properties fetched: {len(properties)}")
    return properties



# Function to update Firebase
def update_firebase(properties):
    if not properties:
        print("❌ No properties found. Nothing to update.")
        return

    print(f"📝 Found {len(properties)} properties. Updating Firebase...")

    # (Optional) Clear old properties before updating
    docs = db.collection("properties").stream()
    for doc in docs:
        doc.reference.delete()
    print("🗑️ Cleared old properties.")

    # Add all new properties
    for property in properties:
        address = property.get("formattedAddress", "Unknown Address")
        if address == "Unknown Address":
            print(f"⚠️ Skipping property due to missing address: {json.dumps(property, indent=2)}")
            continue

        document_id = address.replace(" ", "_").replace(",", "").replace(".", "")
        rent_estimate = property.get("rentEstimate", 0)
        last_sold_price = property.get("lastSalePrice", 0)  # Correct field from API
        lot_size = property.get("lotSize", 0)  # Correct field for land size

        # ✅ Log the full data before writing to Firebase
        print(f"📦 Data to be stored in Firebase for {document_id}:")
        print(json.dumps({
            "address": address,
            "rent_estimate": rent_estimate,
            "last_sold_price": last_sold_price,
            "lot_size": lot_size
        }, indent=2))

        doc_ref = db.collection("properties").document(document_id)
        
        try:
            doc_ref.set({
                "address": address,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "lot_size": lot_size
            })
            print(f"✅ Successfully added to Firebase: {address}")
        except Exception as e:
            print(f"❌ Error writing to Firebase: {e}")

    print("🔥 Firebase update complete!")


    # (Optional) Clear old properties before updating
    docs = db.collection("properties").stream()
    for doc in docs:
        doc.reference.delete()
    print("🗑️ Cleared old properties.")

    for property in properties:
        address = property.get("formattedAddress", "Unknown Address")
        if address == "Unknown Address":
            print(f"⚠️ Skipping property due to missing address: {json.dumps(property, indent=2)}")
            continue

        document_id = address.replace(" ", "_").replace(",", "").replace(".", "")
        rent_estimate = property.get("rentEstimate", 0)
        last_sold_price = property.get("lastSalePrice", 0)  # Correct field from API
        lot_size = property.get("lotSize", 0)  # Correct field for land size

        doc_ref = db.collection("properties").document(document_id)
        
        try:
            doc_ref.set({
                "address": address,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "lot_size": lot_size
            })
            print(f"✅ Added property to Firebase: {address}")
        except Exception as e:
            print(f"❌ Error writing to Firebase: {e}")

    print("🔥 Firebase update complete!")


    # (Optional) Clear old properties before updating
    docs = db.collection("properties").stream()
    for doc in docs:
        doc.reference.delete()
    print("🗑️ Cleared old properties.")

    # Add all new properties
    for property in properties:
        address = property.get("address", "Unknown Address")
        if address == "Unknown Address":
            print("⚠️ Skipping property with missing address")
            continue

        print(f"📝 Writing to Firebase: {property}")  # Debugging log
        doc_ref = db.collection("properties").document(address.replace(" ", "_"))
        doc_ref.set(property)
        print(f"✅ Added: {address}")

    print("🔥 Firebase update complete!")


# Fetch data and update Firebase
properties = fetch_property_data()
if properties:
    update_firebase(properties)
    print("✅ Data successfully updated in Firebase!")
else:
    print("❌ No properties found.")

