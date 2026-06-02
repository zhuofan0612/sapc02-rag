from dotenv import load_dotenv
from anthropic import Anthropic
import os

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1000
