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
  if (!value) return "N/A";
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}

// Function to format area values
function formatArea(value) {
  if (!value) return "N/A";
  return new Intl.NumberFormat('en-US').format(value) + " sq ft";
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

        content += `
        <div class="property-count">Found ${querySnapshot.size} properties</div>
        `;

        querySnapshot.forEach((doc) => {
            const data = doc.data();
            content += `
                <div class="property">
                    <h3>${data.address || "Unknown Address"}</h3>
                    <div class="property-details">
                        <p><strong>Last Sale Price:</strong> ${formatCurrency(data.last_sold_price)}</p>
                        <p><strong>Rent Estimate:</strong> ${formatCurrency(data.rent_estimate)}/month</p>
                        <p><strong>Lot Size:</strong> ${formatArea(data.lot_size)}</p>
                        <p><strong>Bedrooms:</strong> ${data.bedrooms || "N/A"}</p>
                        <p><strong>Bathrooms:</strong> ${data.bathrooms || "N/A"}</p>
                    </div>
                </div>
            `;
        });

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
