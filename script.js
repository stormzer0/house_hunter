// Import Firebase modules from CDN
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getFirestore, collection, getDocs } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-firestore.js";

// Your Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCkqPOT4HiCvNJZpethDyPAQ6BlzWg3qqg",
  authDomain: "house-hunter-b3607.firebaseapp.com",
  projectId: "house-hunter-b3607",
  storageBucket: "house-hunter-b3607.firebasestorage.app",
  messagingSenderId: "594223797598",
  appId: "1:594223797598:web:71f7b41d8ade93b0506bcf"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// Function to format currency values
function formatCurrency(value) {
  if (!value || value === 0) return "N/A";
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}

// Function to format area values
function formatArea(value) {
  if (!value || value === 0) return "N/A";
  return new Intl.NumberFormat('en-US').format(value) + " sq ft";
}

// Format bedrooms and bathrooms
function formatRooms(value) {
  if (!value || value === 0) return "N/A";
  return value;
}

// Calculate cap rate
function calculateCapRate(rentEstimate, propertyValue) {
  if (!rentEstimate || !propertyValue || rentEstimate === 0 || propertyValue === 0) return "N/A";
  const annualRent = rentEstimate * 12;
  const capRate = (annualRent / propertyValue) * 100;
  return capRate.toFixed(2) + "%";
}

// Function to fetch property data from Firestore
async function fetchProperties() {
    try {
        const querySnapshot = await getDocs(collection(db, "properties"));
        let content = "<h2>North Fork Property Listings</h2>";
        
        if (querySnapshot.empty) {
            document.getElementById("property-data").innerHTML = 
                "<p>No properties found. Please check back later.</p>";
            return;
        }

        // Convert to array for sorting
        const propertiesArray = [];
        querySnapshot.forEach((doc) => {
            propertiesArray.push(doc.data());
        });
        
        // Sort by property value (highest to lowest)
        propertiesArray.sort((a, b) => b.property_value - a.property_value);

        content += `
        <div class="property-count">Found ${propertiesArray.length} properties - Filtered to $100K-$1.2M value range</div>
        `;

        for (const data of propertiesArray) {
            // Add sale date if available
            let saleInfo = formatCurrency(data.last_sold_price);
            if (data.last_sale_date) {
                saleInfo += ` (${data.last_sale_date})`;
            }
            
            // Calculate cap rate
            const capRate = calculateCapRate(data.rent_estimate, data.property_value);
            
            content += `
                <div class="property">
                    <h3>${data.address || "Unknown Address"}</h3>
                    <div class="property-details">
                        <p><strong>Property Value:</strong> ${formatCurrency(data.property_value)}</p>
                        <p><strong>Last Sale Price:</strong> ${saleInfo}</p>
                        <p><strong>Monthly Rent:</strong> ${formatCurrency(data.rent_estimate)}</p>
                        <p><strong>Cap Rate:</strong> ${capRate}</p>
                        <p><strong>Lot Size:</strong> ${formatArea(data.lot_size)}</p>
                        <p><strong>Bedrooms:</strong> ${formatRooms(data.bedrooms)}</p>
                        <p><strong>Bathrooms:</strong> ${formatRooms(data.bathrooms)}</p>
                    </div>
                </div>
            `;
        }

        document.getElementById("property-data").innerHTML = content;
    } catch (error) {
        console.error("Error fetching properties:", error);
        document.getElementById("property-data").innerHTML = 
            `<p>Error loading properties: ${error.message}</p>`;
    }
}

// Fetch properties when the page loads
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("property-data").innerHTML = "<p>Loading properties...</p>";
    fetchProperties();
});
