import os, sys

# edit your path below
sys.path.append("/home/cyranicusmcneff.helioho.st/httpdocs/server");

sys.path.insert(0, os.path.dirname(__file__))
from app import app as application

# set this to something harder to guess
application.secret_key = 'secret'
