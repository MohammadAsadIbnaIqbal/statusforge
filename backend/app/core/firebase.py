import json
import logging
import firebase_admin
from firebase_admin import credentials
from .config import settings

logger = logging.getLogger(__name__)

def initialize_firebase():
    # Only initialize if not already initialized
    if not firebase_admin._apps:
        # Check if all required credentials exist
        if settings.FIREBASE_PROJECT_ID and settings.FIREBASE_CLIENT_EMAIL and settings.FIREBASE_PRIVATE_KEY:
            try:
                # Reconstruct the private key replacing escaped newlines
                private_key = settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n')
                
                cert_dict = {
                    "type": "service_account",
                    "project_id": settings.FIREBASE_PROJECT_ID,
                    "private_key_id": "", # Not strictly required for token verification
                    "private_key": private_key,
                    "client_email": settings.FIREBASE_CLIENT_EMAIL,
                    "client_id": "",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL}"
                }
                
                cred = credentials.Certificate(cert_dict)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin: {e}")
        else:
            logger.warning("Firebase Admin credentials not fully configured. Firebase Auth will not work.")
            
initialize_firebase()
