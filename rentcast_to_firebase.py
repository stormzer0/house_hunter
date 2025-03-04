import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
import os
import time
from datetime import datetime
import urllib.parse

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

# Price range filter (in dollars)
MIN_PROPERTY_VALUE = 100000
MAX_PROPERTY_VALUE = 1200000

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

# Process address into format suitable for API
def format_address_for_api(address, city, state, zip_code):
    # Create a fully formatted address with city, state and zip
    full_address = f"{address}, {city}, {state} {zip_code}"
    # URL encode the address
    encoded_address = urllib.parse.quote(full_address)
    return encoded_address

# Function to fetch property data using the standard properties endpoint (GET method)
def fetch_property_data():
    properties = []
    filtered_properties = []
    
    for town in TOWNS:
        city, state = town.split(", ")
        
        # Get properties from the properties endpoint
        print(f"🔍 Fetching properties for {town}...")
        url = f"https://api.rentcast.io/v1/properties?city={urllib.parse.quote(city)}&state={state}&limit=15"
        
        counter.increment()  # Count this API call
        response = requests.get(url, headers=API_HEADERS)
        
        if response.status_code != 200:
            print(f"❌ API Error for {town}: {response.status_code}")
            try:
                print(f"Error details: {response.json()}")
            except:
                print(f"Error text: {response.text}")
            continue
            
        data = response.json()
        
        # Debug the response structure
        with open(f"{city.lower()}_response.json", "w") as f:
            json.dump(data, f, indent=2)
        
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
        
        # For each property, extract existing data
        for prop in town_properties:
            address = None
            for addr_field in ["formattedAddress", "address", "formatted_address"]:
                if addr_field in prop and prop[addr_field]:
                    address = prop[addr_field]
                    break
            
            if not address:
                print("⚠️ Skipping property with missing address")
                continue
                
            # Extract basic property info
            bedrooms = prop.get("bedrooms", 0)
            bathrooms = prop.get("bathrooms", 0)
            lot_size = prop.get("lotSize", 0)
            zip_code = prop.get("zipCode", "11944")  # Default to Greenport ZIP
            
            # Format address for API calls
            full_address = format_address_for_api(address, city, state, zip_code)
            
            # Get property value first to apply our filter
            property_value = 0
            last_sold_price = 0
            last_sale_date = ""
            try:
                print(f"  Getting property value for: {address}")
                counter.increment()
                value_url = f"https://api.rentcast.io/v1/avm/value?address={full_address}"
                
                value_response = requests.get(value_url, headers=API_HEADERS)
                
                if value_response.status_code == 200:
                    value_data = value_response.json()
                    
                    # Extract the property value (AVM)
                    if "value" in value_data:
                        property_value = value_data["value"]
                    elif "price" in value_data:
                        property_value = value_data["price"]
                    
                    print(f"  💲 Property value: ${property_value}")
                    
                    # Check if property is within our desired price range
                    if property_value < MIN_PROPERTY_VALUE or property_value > MAX_PROPERTY_VALUE:
                        print(f"  ⚠️ Property value ${property_value} is outside our target range (${MIN_PROPERTY_VALUE}-${MAX_PROPERTY_VALUE})")
                        continue
                    
                    # Proceed with extracting sales history
                    if "lastSaleDate" in value_data and "lastSalePrice" in value_data:
                        last_sold_price = value_data["lastSalePrice"]
                        last_sale_date = value_data["lastSaleDate"]
                        print(f"  🏠 Last sale: ${last_sold_price} on {last_sale_date}")
                    elif "salesHistory" in value_data and len(value_data["salesHistory"]) > 0:
                        # Get most recent sale
                        most_recent = max(value_data["salesHistory"], key=lambda x: x.get("date", ""))
                        last_sold_price = most_recent.get("price", 0)
                        last_sale_date = most_recent.get("date", "")
                        print(f"  🏠 Last sale: ${last_sold_price} on {last_sale_date}")
                else:
                    print(f"  ⚠️ Failed to get property value: {value_response.status_code}")
                    print(f"  Response: {value_response.text[:200]}")  # Show first 200 chars of response
                    continue  # Skip this property if we can't get its value
            except Exception as e:
                print(f"  ❌ Error getting property value: {e}")
                continue  # Skip this property if we encounter an error
            
            # Only proceed with rent estimate if the property value is in our range
            rent_estimate = 0
            try:
                print(f"  Getting rent estimate for: {address}")
                counter.increment()
                rent_url = f"https://api.rentcast.io/v1/avm/rent/long-term?address={full_address}"
                
                rent_response = requests.get(rent_url, headers=API_HEADERS)
                
                if rent_response.status_code == 200:
                    rent_data = rent_response.json()
                    
                    # Extract rent value from response
                    if "rent" in rent_data:
                        rent_estimate = rent_data["rent"]
                    elif "rentLongTerm" in rent_data:
                        rent_estimate = rent_data["rentLongTerm"]
                    print(f"  💰 Rent estimate: ${rent_estimate}")
                else:
                    print(f"  ⚠️ Failed to get rent estimate: {rent_response.status_code}")
            except Exception as e:
                print(f"  ❌ Error getting rent estimate: {e}")
            
            # Create a property object with all our data
            enhanced_prop = {
                "address": address,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "lot_size": lot_size,
                "property_value": property_value,
                "rent_estimate": rent_estimate,
                "last_sold_price": last_sold_price,
                "last_sale_date": last_sale_date,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Add to our filtered list
            filtered_properties.append(enhanced_prop)
            print(f"  ✅ Added property to filtered list: {address} (${property_value})")
            
            # Respect API rate limits
            time.sleep(1)
    
    print(f"🏡 Total properties after filtering: {len(filtered_properties)} (out of {len(properties)} found)")
    print(f"📞 Total API calls made: {counter.get_count()}")
    return filtered_properties

# Function to update Firebase
def update_firebase(properties):
    if not properties:
        print("❌ No properties found. Nothing to update.")
        return

    print(f"📝 Found {len(properties)} properties. Updating Firebase...")

    # Don't clear all properties if we didn't find any new ones
    if len(properties) < 3:
        print("⚠️ Too few properties found, not clearing existing database.")
    else:
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
                print(f"✅ Added: {address}")
                print(f"  - Value: ${property['property_value']}")
                print(f"  - Rent: ${property['rent_estimate']}")
                print(f"  - Last Sold: ${property['last_sold_price']} on {property['last_sale_date']}")
        except Exception as e:
            print(f"❌ Error writing to Firebase: {e}")

    print(f"🔥 Firebase update complete! Added {added_count} properties.")

# Main execution
print("🚀 Starting property data fetch with price filtering...")
print(f"📊 Only including properties valued between ${MIN_PROPERTY_VALUE} and ${MAX_PROPERTY_VALUE}")
properties = fetch_property_data()
if properties:
    update_firebase(properties)
    print("✅ Data successfully updated in Firebase!")
    print(f"📊 SUMMARY: Made {counter.get_count()} API calls to fetch {len(properties)} properties")
else:
    print("❌ No properties found after filtering.")
