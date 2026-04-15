import argparse
import secrets
import sys

from database import Database
from models.user import User


def parse_args():
    parser = argparse.ArgumentParser(
        description='Promote an existing user to admin, or create then promote if missing.'
    )
    parser.add_argument('--email', required=True, help='Target user email')
    parser.add_argument('--password', help='Required only when user does not exist')
    parser.add_argument('--auto-password', action='store_true', help='Auto-generate a strong password if user does not exist')
    parser.add_argument('--username', help='Optional username if creation is needed')
    parser.add_argument('--full-name', default='', help='Optional full name if creation is needed')
    return parser.parse_args()


def main():
    args = parse_args()

    if not Database.initialize():
        print('Failed to connect to database')
        return 1

    User.initialize()
    users = Database.get_collection('users')

    email = args.email.strip().lower()
    existing = users.find_one({'email': email})
    generated_password = None

    if not existing:
        password_to_use = args.password
        if not password_to_use and args.auto_password:
            generated_password = secrets.token_urlsafe(14)
            password_to_use = generated_password

        if not password_to_use:
            print('User not found. Provide --password or use --auto-password to create this user safely using existing hashing logic.')
            return 1

        username = (args.username or email.split('@')[0]).strip()
        created, status = User.create_user(
            username=username,
            email=email,
            password=password_to_use,
            full_name=args.full_name,
        )
        if status != 201:
            print(f"Failed to create user: {created.get('error', 'unknown error')}")
            return 1

    result = users.update_one({'email': email}, {'$set': {'is_admin': True}})
    if result.matched_count == 0:
        print('No user matched the target email')
        return 1

    user = users.find_one({'email': email}, {'password_hash': 0}) or {}
    print('Admin user configured successfully')
    print(f"email={user.get('email', '')}")
    print(f"username={user.get('username', '')}")
    print(f"is_admin={user.get('is_admin', False)}")
    if generated_password:
        print(f"generated_password={generated_password}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
