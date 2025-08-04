import os, sys

sys.path.append("/home/cyranicusmcneff.helioho.st/httpdocs/server")
sys.path.insert(0, os.path.dirname(__file__))

from server.app import app as application

application.secret_key = "key"
