"""
Minimal MongoDB Atlas connectivity check (Python + PyMongo).

Install and run (PowerShell):
1) pip install pymongo
2) $env:MONGODB_URI="<your-atlas-uri>"; python mongodbPing.py

If MONGODB_URI is not set in the environment, this script falls back to
mongodb_config.json in the same folder, expecting a key named MONGODB_URI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

CONFIG_FILE = Path("mongodb_config.json")


def load_config_file() -> dict[str, Any]:
    """Load optional local JSON config for fallback settings."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        config_data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("mongodb_config.json exists but is not valid JSON.") from exc

    if not isinstance(config_data, dict):
        raise RuntimeError("mongodb_config.json must contain a JSON object.")

    return config_data


def get_mongodb_uri(config_data: dict[str, Any]) -> str:
    """Read MongoDB URI from env first, then from a local JSON config file."""
    env_uri = os.getenv("MONGODB_URI")
    if env_uri and env_uri.strip():
        print("[1/6] Found MONGODB_URI in environment variables.")
        return env_uri.strip()

    print("[1/6] MONGODB_URI not found in environment. Trying mongodb_config.json...")

    if not CONFIG_FILE.exists():
        raise RuntimeError(
            "Could not find MONGODB_URI. Set it as an environment variable or add "
            "mongodb_config.json with {\"MONGODB_URI\": \"<your-uri>\"}."
        )

    file_uri = config_data.get("MONGODB_URI")
    if isinstance(file_uri, str) and file_uri.strip():
        print("[1/6] Loaded MONGODB_URI from mongodb_config.json.")
        return file_uri.strip()

    raise RuntimeError(
        "mongodb_config.json was found, but MONGODB_URI is missing or empty."
    )


def main() -> None:
    client: MongoClient | None = None

    try:
        config_data = load_config_file()
        uri = get_mongodb_uri(config_data)
        db_name = (os.getenv("MONGODB_DB") or str(config_data.get("MONGODB_DB") or "")).strip()
        collection_name = (os.getenv("MONGODB_COLLECTION") or str(config_data.get("MONGODB_COLLECTION") or "")).strip()

        print("[2/6] Connecting to MongoDB Atlas...")
        # Server API v1 keeps client behavior stable across server upgrades.
        client = MongoClient(uri, server_api=ServerApi("1"), serverSelectionTimeoutMS=10000)

        print("[3/6] Sending ping command to verify connectivity...")
        # Ping is a lightweight command that confirms the server is reachable.
        client.admin.command("ping")

        print("[4/6] Success: Connected to MongoDB Atlas and ping succeeded.")

        if not db_name:
            print("[5/6] No database selected. Set MONGODB_DB to access your data.")
            print("[6/6] Finished connectivity check.")
            return

        print(f"[5/6] Accessing database '{db_name}'...")
        database = client[db_name]

        if not collection_name:
            collections = database.list_collection_names()
            if collections:
                print("[6/6] Connected to database. Collections found:")
                for name in collections:
                    print(f"  - {name}")
            else:
                print("[6/6] Connected to database. No collections found yet.")
            return

        print(f"[6/6] Reading a small sample from collection '{collection_name}'...")
        collection = database[collection_name]
        total_docs = collection.count_documents({})
        sample_docs = list(collection.find({}, {"_id": 0}).limit(3))

        print(f"[data] Total documents in '{collection_name}': {total_docs}")
        if sample_docs:
            print("[data] Up to 3 sample documents (without _id):")
            for index, doc in enumerate(sample_docs, start=1):
                print(f"  {index}. {doc}")
        else:
            print("[data] Collection is reachable, but currently empty.")

    except RuntimeError as err:
        print(f"[ERROR] Configuration issue: {err}")
    except PyMongoError as err:
        print(f"[ERROR] MongoDB connection/ping failed: {err}")
    except Exception as err:  # Keeps beginner output clear for unexpected issues.
        print(f"[ERROR] Unexpected failure: {err}")
    finally:
        if client is not None:
            print("[cleanup] Closing MongoDB connection...")
            client.close()
            print("[cleanup] Connection closed.")


if __name__ == "__main__":
    main()
