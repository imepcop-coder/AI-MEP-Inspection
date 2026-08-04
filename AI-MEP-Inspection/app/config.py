import os
from dotenv import load_dotenv

load_dotenv()

# AI Provider
AI_PROVIDER = os.getenv("AI_PROVIDER", "nvidia").lower()

# API Keys
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Models
NVIDIA_MODEL = os.getenv(
    "NVIDIA_MODEL",
    "meta/llama-3.2-90b-vision-instruct"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)