import os, sys
from pathlib import Path

# 1) Point sys.path to your server/app.py folder:
sys.path.append("/home/cyranicusmcneff.helioho.st/httpdocs")
# 2) Import and expose the Flask app as "application":
from server.app import app as application

# 3) Optional: force a fixed secret key (sessions, CSRF, etc.)
application.secret_key = 'YourSecretKeyHere'

# (You don’t need application_root since it's mounted at "/")
