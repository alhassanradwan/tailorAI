from pymongo import MongoClient
from config import Config

client = MongoClient('mongodb://localhost:27017/')
db = client['adaptiveai']

# Update the admin user to have is_admin flag
admin_email = Config.ADMIN_EMAIL  # hassangrdwan@gmail.com
result = db['users'].update_one(
    {'email': admin_email},
    {'$set': {'is_admin': True}}
)

if result.matched_count > 0:
    print(f"✅ Updated {admin_email} to admin")
    # Show the updated user
    admin_user = db['users'].find_one({'email': admin_email}, {'password_hash': 0})
    print(f"\nAdmin user details:")
    print(f"  Email: {admin_user.get('email')}")
    print(f"  Username: {admin_user.get('username')}")
    print(f"  is_admin: {admin_user.get('is_admin')}")
    print(f"  Created: {admin_user.get('created_at')}")
else:
    print(f"❌ User {admin_email} not found")
