// Import Firebase
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

// Function to fetch properties from Firestore
async function fetchProperties() {
    const querySnapshot = await getDocs(collection(db, "properties"));
    let content = "<h2>Property Listings</h2>";

    querySnapshot.forEach((doc) => {
        const data = doc.data();
        content += `
            <div class="property">
                <h3>${data.address || "Unknown Address"}</h3>
                <p><strong>Rent Estimate:</strong> $${data.rent_estimate || "N/A"}</p>
                <p><strong>Last Sale Price:</strong> $${data.last_sold_price || "N/A"}</p>
            </div>
            <hr>
        `;
    });

    document.getElementById("property-data").innerHTML = content;
}

// Run function when the page loads
document.addEventListener("DOMContentLoaded", fetchProperties);
