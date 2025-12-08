import streamlit as st
from pymongo import MongoClient
import bcrypt

# ----------------- DATABASE CONNECTION -----------------
MONGO_URI = st.secrets.get("MONGO_URI")

if not MONGO_URI:
    st.error("❌ MONGO_URI not found in secrets.toml")
    st.stop()

client = MongoClient(MONGO_URI)
db = client["youtube_dashboard"]
users_collection = db["users"]


# ----------------- SIGNUP FUNCTION -----------------
def signup(email, password):
    """Create a new user with hashed password."""
    try:
        if users_collection.find_one({"email": email}):
            return False, "⚠️ Email already registered!"

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        users_collection.insert_one({
            "email": email,
            "password": hashed_pw
        })

        return True, "✅ Signup successful! Please log in."

    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ----------------- LOGIN FUNCTION -----------------
def login(email, password):
    """Verify user credentials using bcrypt."""
    try:
        user = users_collection.find_one({"email": email})
        if not user:
            return False, "⚠️ User not found!"

        # bcrypt validation
        if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            return True, "✅ Login successful!"
        else:
            return False, "❌ Invalid password!"

    except Exception as e:
        return False, f"❌ Error: {str(e)}"
