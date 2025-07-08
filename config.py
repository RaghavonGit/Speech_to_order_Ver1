#!/usr/bin/env python3
"""
Configuration file for Speech-to-Text Grocery System
"""

import os
from pathlib import Path

class Config:
    """
    Configuration settings for the grocery order system
    """
    
    # Base directories
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    ORDERS_DIR = BASE_DIR / "orders"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Create directories if they don't exist
    for directory in [DATA_DIR, ORDERS_DIR, LOGS_DIR]:
        directory.mkdir(exist_ok=True)
    
    # Audio settings
    AUDIO_SETTINGS = {
        'sample_rate': 16000,
        'chunk_size': 1024,
        'channels': 1,
        'timeout': 5,
        'phrase_time_limit': 10,
        'energy_threshold': 300,
        'dynamic_energy_threshold': True,
        'pause_threshold': 0.8,
        'non_speaking_duration': 0.5
    }
    
    # Speech recognition settings
    SPEECH_RECOGNITION = {
        'engine': 'google',  # Options: google, sphinx, wit, bing, azure
        'language_codes': {
            'tamil': 'ta-IN',
            'telugu': 'te-IN'
        },
        'fallback_language': 'en-IN',
        'confidence_threshold': 0.7
    }
    
    # Language processing settings
    LANGUAGE_PROCESSING = {
        'confidence_threshold': 0.6,
        'fuzzy_match_threshold': 0.7,
        'default_quantity': '1',
        'default_unit': 'piece',
        'max_items_per_order': 50
    }
    
    # Supported languages
    SUPPORTED_LANGUAGES = ['tamil', 'telugu']
    
    # Default language (fallback)
    DEFAULT_LANGUAGE = 'tamil'
    
    # Logging configuration
    LOGGING = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': LOGS_DIR / 'grocery_system.log',
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    # API keys (set as environment variables)
    API_KEYS = {
        'google_speech': os.getenv('GOOGLE_SPEECH_API_KEY'),
        'azure_speech': os.getenv('AZURE_SPEECH_API_KEY'),
        'wit_ai': os.getenv('WIT_AI_API_KEY')
    }
    
    # Database settings (for future expansion)
    DATABASE = {
        'type': 'sqlite',
        'path': BASE_DIR / 'grocery_orders.db'
    }
    
    # Web interface settings (for future expansion)
    WEB_INTERFACE = {
        'host': '127.0.0.1',
        'port': 5000,
        'debug': True
    }
    
    # Common grocery categories
    GROCERY_CATEGORIES = {
        'vegetables': ['tomato', 'onion', 'potato', 'carrot', 'beans'],
        'fruits': ['apple', 'banana', 'orange', 'mango', 'grapes'],
        'grains': ['rice', 'wheat', 'lentils', 'dal'],
        'dairy': ['milk', 'yogurt', 'butter', 'cheese'],
        'spices': ['turmeric', 'chili', 'cumin', 'coriander'],
        'groceries': ['oil', 'salt', 'sugar', 'tea', 'coffee']
    }
    
    # Unit conversions
    UNIT_CONVERSIONS = {
        'kg': 1000,  # grams
        'gram': 1,
        'liter': 1000,  # ml
        'ml': 1,
        'dozen': 12,
        'piece': 1
    }
    
    @classmethod
    def get_language_data_dir(cls, language: str) -> Path:
        """Get data directory for specific language"""
        lang_dir = cls.DATA_DIR / language
        lang_dir.mkdir(exist_ok=True)
        return lang_dir
    
    @classmethod
    def get_orders_file_path(cls, order_id: str) -> Path:
        """Get file path for order"""
        return cls.ORDERS_DIR / f"order_{order_id}.json"
    
    @classmethod
    def validate_language(cls, language: str) -> bool:
        """Check if language is supported"""
        return language.lower() in cls.SUPPORTED_LANGUAGES
    
    @classmethod
    def get_language_code(cls, language: str) -> str:
        """Get language code for speech recognition"""
        return cls.SPEECH_RECOGNITION['language_codes'].get(
            language.lower(), 
            cls.SPEECH_RECOGNITION['fallback_language']
        )