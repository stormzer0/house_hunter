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
        if self.calls % 5 == 0:
            print(f"⚠️ API Call Count: {self.calls}")
        
    def get_count(self):
        return self.calls

# Initialize counter
counter = ApiCallCounter()

# Function to fetch property data using the standard properties endpoint (GET method)
def fetch_property_data():
    properties = []
    
    for town in TOWNS:
        city, state = town.split(", ")
        
        # Use the standard properties endpoint with GET method
        url = f"https://api.rentcast.io/v1/properties?city={city}&state={state}&limit=15"
        
        print(f"🔍 Fetching properties for {town}...")
        counter.increment()  # Count this API call
        response = requests.get(url, headers=API_HEADERS)
        
        if response.status_code != 200:
            print(f"❌ API Error for {town}: {response.status_code}")
            try:
                error_details = response.json()
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except:
                print(f"Error response: {response.text}")
            continue
            
        data = response.json()
        
        # Process the response
        town_properties = []
        if isinstance(data, list):
            town_properties = data
        elif isinstance(data, dict) and "properties" in data:
            town_properties = data["properties"]
        
        if not town_properties:
            print(f"⚠️ No properties found for {town}")
            continue
            
        print(f"✅ Found {len(town_properties)} properties for {town}")
        
        # For each property, get additional details one by one
        for prop in town_properties:
            # Extract address - this is crucial
            address = None
            for addr_field in ["formattedAddress", "address", "formatted_address"]:
                if addr_field in prop and prop[addr_field]:
                    address = prop[addr_field]
                    break
            
            if not address:
                print("⚠️ Skipping property with missing address")
                continue
                
            # Extract other standard fields
            bedrooms = prop.get("bedrooms", 0)
            bathrooms = prop.get("bathrooms", 0)
            lot_size = prop.get("lotSize", 0)
            
            # Get rent estimate using the address
            rent_estimate = 0
            try:
                print(f"  Getting rent estimate for: {address}")
                counter.increment()
                rent_url = f"https://api.rentcast.io/v1/avm/rent?address={address}&bedrooms={bedrooms}&bathrooms={bathrooms}"
                rent_response = requests.get(rent_url, headers=API_HEADERS)
                
                if rent_response.status_code == 200:
                    rent_data = rent_response.json()
                    rent_estimate = rent_data.get("rent", 0)
                    print(f"  💰 Rent estimate: ${rent_estimate}")
                else:
                    print(f"  ⚠️ Failed to get rent estimate: {rent_response.status_code}")
            except Exception as e:
                print(f"  ❌ Error getting rent estimate: {e}")
            
            # Get sales data using the address
            last_sold_price = 0
            last_sale_date = ""
            try:
                print(f"  Getting sales data for: {address}")
                counter.increment()
                sales_url = f"https://api.rentcast.io/v1/sales?address={address}"
                sales_response = requests.get(sales_url, headers=API_HEADERS)
                
                if sales_response.status_code == 200:
                    sales_data = sales_response.json()
                    
                    if isinstance(sales_data, list) and len(sales_data) > 0:
                        # Find the most recent sale
                        most_recent = max(sales_data, key=lambda x: x.get("date", ""))
                        last_sold_price = most_recent.get("amount", 0)
                        last_sale_date = most_recent.get("date", "")
                        print(f"  🏠 Last sale: ${last_sold_price} on {last_sale_date}")
                    elif isinstance(sales_data, dict) and "sales" in sales_data:
                        sales_list = sales_data["sales"]
                        if sales_list:
                            most_recent = max(sales_list, key=lambda x: x.get("date", ""))
                            last_sold_price = most_recent.get("amount", 0)
                            last_sale_date = most_recent.get("date", "")
                            print(f"  🏠 Last sale: ${last_sold_price} on {last_sale_date}")
                else:
                    print(f"  ⚠️ Failed to get sales data: {sales_response.status_code}")
            except Exception as e:
                print(f"  ❌ Error getting sales data: {e}")
            
            # Create a property object with all our data
            enhanced_prop = {
                "address": address,
                "city": city,
                "state": state,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "lot_size": lot_size,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "last_sale_date": last_sale_date,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            properties.append(enhanced_prop)
            
            # Add a small delay between properties to respect rate limits
            time.sleep(1)
    
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
        
        try:
            doc_ref = db.collection("properties").document(document_id)
            doc_ref.set(property)
            added_count += 1
            if added_count <= 3 or added_count % 10 == 0:
                print(f"✅ Added: {address} - Rent: ${property['rent_estimate']}, Last Sold: ${property['last_sold_price']}")
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
else:
    print("❌ No properties found.")
