from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['adaptiveai']

# List all collections
print("=== Collections in 'adaptiveai' database ===")
for name in db.list_collection_names():
    count = db[name].count_documents({})
    print(f"  {name}: {count} documents")

# List all users
print("\n=== Users ===")
users = list(db['users'].find({}, {'password_hash': 0}))
print(f"Total users: {len(users)}")
for u in users:
    print(f"  Email: {u.get('email', '?')}")
    print(f"  Username: {u.get('username', '?')}")
    print(f"  Created: {u.get('created_at', '?')}")
    print(f"  ID: {u.get('_id', '?')}")
    print("  ---")

if len(users) == 0:
    print("\n  No users found! Users may have been saved to localStorage instead.")
    print("  This happens when the backend was not running during signup.")
