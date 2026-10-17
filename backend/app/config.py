"""Settings read from environment variables (or a .env file)."""

import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "claude-haiku-5-5")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./tasks.db")
APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/London"))

# How many follow-up questions the AI may ask per task before it must guess.
MAX_FOLLOW_UPS = 2

# Defaults used when the AI can't give a value and no questions are left.
DEFAULT_MINUTES = 30
DEFAULT_CONSEQUENCE = 3
