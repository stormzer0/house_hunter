import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
import os
import time

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
API_HEADERS = {"X-Api-Key": API_KEY, "Accept": "application/json"}

# List of towns we want to track
TOWNS = ["Greenport, NY", "Southold, NY", "East Hampton, NY"]

# Function to fetch property data using multiple endpoints
def fetch_property_data():
    properties = []
    
    for town in TOWNS:
        city, state = town.split(", ")  # Split "Greenport, NY" into "Greenport" and "NY"
        
        # Step 1: Get basic property data first
        properties_url = f"https://api.rentcast.io/v1/properties?city={city}&state={state}&limit=50"
        
        print(f"🔍 Fetching properties for {town}...")
        response = requests.get(properties_url, headers=API_HEADERS)
        
        if response.status_code != 200:
            print(f"❌ API Error for {town}: {response.status_code}")
            continue
            
        # Process property data
        data = response.json()
        town_properties = []
        
        if isinstance(data, list) and len(data) > 0:
            town_properties = data
        elif isinstance(data, dict) and "properties" in data and len(data["properties"]) > 0:
            town_properties = data["properties"]
        else:
            print(f"⚠️ Unexpected or empty response format for {town}")
            continue
            
        print(f"✅ Found {len(town_properties)} properties for {town}")
        
        # Step 2: For each property, get additional details including rent estimates
        for i, prop in enumerate(town_properties):
            # Extract the address
            address = None
            for field in ["formattedAddress", "address", "formatted_address"]:
                if field in prop and prop[field]:
                    address = prop[field]
                    break
                    
            if not address:
                print(f"⚠️ Skipping property with missing address")
                continue
                
            # Extract property ID if available
            property_id = prop.get("id")
            
            # Get rent estimate using the property address
            # According to the API docs, we need to use the /avm/rent endpoint for this
            enhanced_prop = prop.copy()  # Create a copy to add additional info
            
            # Try to get rent estimate using the address
            try:
                rent_url = f"https://api.rentcast.io/v1/avm/rent?address={address}"
                rent_response = requests.get(rent_url, headers=API_HEADERS)
                
                if rent_response.status_code == 200:
                    rent_data = rent_response.json()
                    rent_estimate = rent_data.get("rent")
                    if rent_estimate:
                        enhanced_prop["rentEstimate"] = rent_estimate
                        print(f"💰 Found rent estimate for {address}: ${rent_estimate}")
                else:
                    print(f"⚠️ Failed to get rent estimate for {address}: {rent_response.status_code}")
            except Exception as e:
                print(f"❌ Error getting rent estimate: {e}")
                
            # Try to get sales history using the property ID or address
            try:
                if property_id:
                    sales_url = f"https://api.rentcast.io/v1/properties/{property_id}/sales"
                else:
                    sales_url = f"https://api.rentcast.io/v1/sales?address={address}"
                    
                sales_response = requests.get(sales_url, headers=API_HEADERS)
                
                if sales_response.status_code == 200:
                    sales_data = sales_response.json()
                    
                    # Process based on response format (array or object)
                    sales_history = []
                    if isinstance(sales_data, list):
                        sales_history = sales_data
                    elif isinstance(sales_data, dict) and "sales" in sales_data:
                        sales_history = sales_data["sales"]
                    
                    if sales_history:
                        # Get the most recent sale
                        most_recent_sale = max(sales_history, key=lambda sale: sale.get("date", ""))
                        enhanced_prop["lastSalePrice"] = most_recent_sale.get("amount")
                        enhanced_prop["lastSaleDate"] = most_recent_sale.get("date")
                        print(f"🏠 Found last sale price for {address}: ${enhanced_prop['lastSalePrice']}")
            except Exception as e:
                print(f"❌ Error getting sales history: {e}")
                
            # Add the enhanced property to our list
            properties.append(enhanced_prop)
            
            # Respect API rate limits (50 requests per minute)
            if i > 0 and i % 20 == 0:
                print(f"⏱️ Pausing for API rate limit...")
                time.sleep(3)  # Add a small delay every 20 properties
    
    print(f"🏡 Total properties with details fetched: {len(properties)}")
    return properties

# Function to update Firebase with more careful field extraction
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
        # Extract address
        address = None
        for addr_field in ["formattedAddress", "address", "formatted_address"]:
            if addr_field in property and property[addr_field]:
                address = property[addr_field]
                break
        
        if not address:
            continue

        document_id = address.replace(" ", "_").replace(",", "").replace(".", "")
        
        # Extract all relevant fields using the correct names from the API
        rent_estimate = property.get("rentEstimate", 0)
        last_sold_price = property.get("lastSalePrice", 0)
        last_sale_date = property.get("lastSaleDate", "")
        lot_size = property.get("lotSize", 0)
        bedrooms = property.get("bedrooms", 0)
        bathrooms = property.get("bathrooms", 0)
        
        # For debugging the first few properties
        if added_count < 3:
            print(f"\n🔍 PROPERTY DETAILS FOR: {address}")
            print(f"  Rent Estimate: ${rent_estimate}")
            print(f"  Last Sold Price: ${last_sold_price}")
            print(f"  Last Sale Date: {last_sale_date}")
            print(f"  Lot Size: {lot_size} sq ft")
            print(f"  Bedrooms: {bedrooms}")
            print(f"  Bathrooms: {bathrooms}")
        
        doc_ref = db.collection("properties").document(document_id)
        
        try:
            property_data = {
                "address": address,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "last_sale_date": last_sale_date,
                "lot_size": lot_size,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms
            }
            
            doc_ref.set(property_data)
            added_count += 1
            if added_count <= 3 or added_count % 10 == 0:
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
