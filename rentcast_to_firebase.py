import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
import os
import time
from datetime import datetime

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
API_KEY = "36952abfe82240b2b29156c67e1426dd"
API_HEADERS = {"X-Api-Key": API_KEY, "Accept": "application/json"}

# List of towns we want to track
TOWNS = ["Greenport, NY", "Southold, NY", "East Hampton, NY"]

# Function to track API calls
class ApiCallCounter:
    def __init__(self):
        self.calls = 0
        
    def increment(self):
        self.calls += 1
        if self.calls % 10 == 0:
            print(f"⚠️ API Call Count: {self.calls}")
        
    def get_count(self):
        return self.calls

# Initialize counter
counter = ApiCallCounter()

# Function to fetch property data using a single call to RentCast property search endpoint
def fetch_property_data():
    properties = []
    
    for town in TOWNS:
        city, state = town.split(", ")
        
        # We're going to use the property details endpoint which includes valuations in a single call
        # This is more efficient than making separate calls for rent and sales data
        search_url = f"https://api.rentcast.io/v1/properties/search"
        payload = {
            "city": city,
            "state": state,
            "limit": 15,  # Limit to 15 properties per town to conserve API calls
            "includeValuations": True  # This should include rent estimates
        }
        
        print(f"🔍 Fetching properties for {town}...")
        counter.increment()  # Count this API call
        response = requests.post(search_url, headers=API_HEADERS, json=payload)
        
        if response.status_code != 200:
            print(f"❌ API Error for {town}: {response.status_code}")
            continue
            
        data = response.json()
        
        # Save the raw response to a file for debugging
        with open(f"{city.lower()}_search_response.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Process the results
        if "results" in data and len(data["results"]) > 0:
            print(f"✅ Found {len(data['results'])} properties for {town}")
            
            # Log the structure of the first result to understand the data format
            if len(data["results"]) > 0:
                first_property = data["results"][0]
                print(f"📊 Sample property structure:")
                
                # Check for key fields
                print(f"  - Has address: {'address' in first_property}")
                print(f"  - Has rent estimate: {'rentEstimate' in first_property}")
                print(f"  - Has valuations: {'valuations' in first_property}")
                if "valuations" in first_property:
                    print(f"  - Valuations structure: {list(first_property['valuations'].keys())}")
                print(f"  - Has lastSale: {'lastSale' in first_property}")
                
            # Process and enrich all properties
            for prop in data["results"]:
                # Get rent estimate from the response
                rent_estimate = 0
                if "rentEstimate" in prop:
                    rent_estimate = prop["rentEstimate"]
                elif "valuations" in prop and "rentEstimate" in prop["valuations"]:
                    rent_estimate = prop["valuations"]["rentEstimate"]
                
                # Get sale price from the response
                last_sold_price = 0
                last_sale_date = ""
                if "lastSale" in prop and prop["lastSale"]:
                    if "price" in prop["lastSale"]:
                        last_sold_price = prop["lastSale"]["price"]
                    if "date" in prop["lastSale"]:
                        last_sale_date = prop["lastSale"]["date"]
                
                # Create enhanced property with all the data we need
                enhanced_prop = {
                    "address": prop.get("address", ""),
                    "city": city,
                    "state": state,
                    "bedrooms": prop.get("bedrooms", 0),
                    "bathrooms": prop.get("bathrooms", 0),
                    "lot_size": prop.get("lotSize", 0),
                    "rent_estimate": rent_estimate,
                    "last_sold_price": last_sold_price,
                    "last_sale_date": last_sale_date,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                properties.append(enhanced_prop)
        else:
            print(f"⚠️ No properties found for {town}")
    
    print(f"🏡 Total properties fetched: {len(properties)}")
    print(f"📞 Total API calls made: {counter.get_count()}")
    return properties

# Function to update Firebase
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
        address = property.get("address")
        if not address:
            print("⚠️ Skipping property with missing address")
            continue

        document_id = address.replace(" ", "_").replace(",", "").replace(".", "")
        
        # Add the property to Firebase
        doc_ref = db.collection("properties").document(document_id)
        
        try:
            doc_ref.set(property)
            added_count += 1
            if added_count <= 3 or added_count % 10 == 0:
                print(f"✅ Added: {address}")
                
                # For debugging, print out specific values
                if added_count <= 3:
                    print(f"  - Rent Estimate: ${property['rent_estimate']}")
                    print(f"  - Last Sold Price: ${property['last_sold_price']}")
                    print(f"  - Last Sale Date: {property['last_sale_date']}")
        except Exception as e:
            print(f"❌ Error writing to Firebase: {e}")

    print(f"🔥 Firebase update complete! Added {added_count} properties.")

# Main execution
print("🚀 Starting property data fetch...")
properties = fetch_property_data()
if properties:
    update_firebase(properties)
    print("✅ Data successfully updated in Firebase!")
    print(f"📊 SUMMARY: Made {counter.get_count()} API calls to fetch {len(properties)} properties")
    print(f"💡 With 1000 calls/month limit and running 2x weekly, you should aim for ~125 calls per run")
else:
    print("❌ No properties found.")
