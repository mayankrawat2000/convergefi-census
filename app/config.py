import os
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

# Default Model for Chat and Agent reasoning
DEFAULT_MODEL = "gpt-oss-120b"

# Dynamically determine the base path (works on both host and inside container)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, "artifacts")
HISTORY_DIR = os.path.join(WORKSPACE_DIR, "history")
