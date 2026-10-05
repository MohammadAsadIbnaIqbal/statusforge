import pytest
import firebase_admin
from app.core.firebase import initialize_firebase
from app.core.config import settings

def test_firebase_initialization_missing_credentials(caplog):
    # Temporarily unset variables
    original_project_id = settings.FIREBASE_PROJECT_ID
    settings.FIREBASE_PROJECT_ID = None
    
    # Try to initialize
    initialize_firebase()
    
    assert "Firebase Admin credentials not fully configured" in caplog.text
    
    # Restore
    settings.FIREBASE_PROJECT_ID = original_project_id
