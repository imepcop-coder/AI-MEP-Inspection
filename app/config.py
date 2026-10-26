import os
from dotenv import load_dotenv

load_dotenv()

# AI Provider
AI_PROVIDER = os.getenv("AI_PROVIDER", "bedrock").lower()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
ANTHROPIC_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Models
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "anthropic.claude-sonnet-4-20250514-v1:0")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)