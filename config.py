import os

class Config:
    """Configuration class for the application."""
    
    PORT = 8000
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')