import os, sys
from pathlib import Path

# 1) Point sys.path to your server/app.py folder:
base = Path(__file__).parent
sys.path.insert(0, str(base / 'server'))

# 2) Import and expose the Flask app as "application":
from server.app import app as application

# 3) Optional: force a fixed secret key (sessions, CSRF, etc.)
application.secret_key = "key"

# (You don’t need application_root since it's mounted at "/")
