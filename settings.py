# settings.py — loads environment variables from .env
# Import this at the top of any file that needs API keys

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file and puts variables into os.environ

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
