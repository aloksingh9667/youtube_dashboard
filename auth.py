from pymongo import MongoClient
import bcrypt

# ----------------- MONGODB CONNECTION -----------------
MONGO_URI = "mongodb+srv://NovaAI:Abcd1234@cluster0.at3duas.mongodb.net/Youtube?retryWrites=true&w=majority&appName=Cluster0"  # Replace with your Atlas URI
client = MongoClient(MONGO_URI)
db = client["youtube_dashboard"]
users_collection = db["users"]


# ----------------- SIGNUP -----------------
def signup(email, password):
    if users_collection.find_one({"email": email}):
        return False, "⚠️ Email already registered!"

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users_collection.insert_one({"email": email, "password": hashed_pw})
    return True, "✅ Signup successful! Please login."


# ----------------- LOGIN -----------------
def login(email, password):
    user = users_collection.find_one({"email": email})
    if not user:
        return False, "⚠️ User not found!"

    if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return True, "✅ Login successful!"
    else:
        return False, "❌ Invalid password!"
