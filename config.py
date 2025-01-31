# config.py
import os
from typing import Optional

def get_google_api_key() -> Optional[str]:
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    return api_key