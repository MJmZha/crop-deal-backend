"""
Firebase Admin SDK initialization and Firestore client.
"""
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()


def init_firebase():
    """Initialize Firebase Admin SDK and return Firestore client."""
    try:
        if not firebase_admin._apps:
            cred_path = (
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                or os.getenv("FIREBASE_CREDENTIALS_PATH")
                or "firebase-credentials.json"
            )

            if not os.path.exists(cred_path):
                print(f"[WARN] Firebase credentials file not found: {cred_path}")
                print("[WARN] Firebase features will be DISABLED.")
                return None

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(
                cred,
                {"projectId": os.getenv("FIREBASE_PROJECT_ID", "crop-deal-risk-system")},
            )
            print("[OK] Firebase connected successfully!")
            print(f"[OK] Project: {os.getenv('FIREBASE_PROJECT_ID', 'crop-deal-risk-system')}")

        return firestore.client()

    except Exception as exc:
        print(f"[ERROR] Firebase connection failed: {exc}")
        return None


# Global Firestore client
db = init_firebase()
