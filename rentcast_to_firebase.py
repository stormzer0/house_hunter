import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Load Firebase credentials from GitHub Secret
firebase_key_content = os.getenv("FIREBASE_KEY")

if not firebase_key_content:
    print("❌ ERROR: FIREBASE_KEY secret is missing! Add it to GitHub Secrets.")
    exit(1)  # Stop the script if no key is found

# Write the key to a file for Firebase SDK
firebase_key_path = "firebase-key.json"
with open(firebase_key_path, "w") as f:
    f.write(firebase_key_content)

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
        
        print(f"🔍 Fetching properties for {town}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Received response for {town}")
            
            # Debug the first property to understand structure
            if isinstance(data, list) and len(data) > 0:
                print(f"📊 Sample property structure for {town}:")
                print(json.dumps(data[0], indent=2))
                properties.extend(data)  # If API returns a list, append directly
            elif isinstance(data, dict) and "properties" in data and len(data["properties"]) > 0:
                print(f"📊 Sample property structure for {town}:")
                print(json.dumps(data["properties"][0], indent=2))
                properties.extend(data["properties"])  # If it's a dictionary, extract "properties"
            else:
                print(f"⚠️ Unexpected or empty response format for {town}")
        else:
            print(f"❌ API Error for {town}: {response.status_code}")
            try:
                print(f"Error details: {response.json()}")
            except:
                print(f"Error details not available as JSON")

    print(f"🏡 Total properties fetched: {len(properties)}")
    return properties

# Function to update Firebase - FIXED VERSION
def update_firebase(properties):
    if not properties:
        print("❌ No properties found. Nothing to update.")
        return

    print(f"📝 Found {len(properties)} properties. Updating Firebase...")

    # Clear old properties before updating
    docs = db.collection("properties").stream()
    deleted_count = 0
    for doc in docs:
        doc.reference.delete()
        deleted_count += 1
    print(f"🗑️ Cleared {deleted_count} old properties.")

    # Add all new properties
    added_count = 0
    for property in properties:
        # Try different possible field names for address
        address = (
            property.get("formattedAddress") or 
            property.get("address") or 
            property.get("formatted_address") or 
            "Unknown Address"
        )
        
        if address == "Unknown Address":
            print(f"⚠️ Skipping property due to missing address")
            continue

        document_id = address.replace(" ", "_").replace(",", "").replace(".", "")
        
        # Try different field names for each property
        rent_estimate = property.get("rentEstimate", property.get("rent_estimate", 0))
        last_sold_price = property.get("lastSalePrice", property.get("last_sale_price", 0))
        lot_size = property.get("lotSize", property.get("lot_size", 0))
        
        # Additional fields you might want to store
        bedrooms = property.get("bedrooms", 0)
        bathrooms = property.get("bathrooms", 0)
        
        doc_ref = db.collection("properties").document(document_id)
        
        try:
            property_data = {
                "address": address,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "lot_size": lot_size,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms
            }
            
            doc_ref.set(property_data)
            added_count += 1
            if added_count <= 3 or added_count % 10 == 0:  # Show some samples and progress
                print(f"✅ Added: {address}")
        except Exception as e:
            print(f"❌ Error writing to Firebase: {e}")

    print(f"🔥 Firebase update complete! Added {added_count} properties.")

# Fetch data and update Firebase
print("🚀 Starting property data fetch...")
properties = fetch_property_data()
if properties:
    update_firebase(properties)
    print("✅ Data successfully updated in Firebase!")
else:
    print("❌ No properties found.")
