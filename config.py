import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Your credentials
    EMAIL = os.getenv("EMAIL")
    SECRET = os.getenv("SECRET")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    
    # AIPipe Configuration
    AIPIPE_API_KEY = os.getenv("AIPIPE_API_KEY")
    AIPIPE_BASE_URL = os.getenv("AIPIPE_BASE_URL", "https://api.aipipe.io/v1")

    # Model Configuration
    MODEL_NAME: str = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", 180))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))
    
    # Browser Configuration
    HEADLESS = True
    BROWSER_TIMEOUT = 30000  # 30 seconds
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ["EMAIL", "SECRET", "AIPIPE_API_KEY"]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

config = Config()
