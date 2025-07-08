# Converted from telugu_processor.txt #!/usr/bin/env python3
"""
Telugu Language Processor
Handles Telugu language grocery orders
"""

from base_processor import BaseLanguageProcessor, GroceryItem
from typing import Dict, List
import re

class TeluguProcessor(BaseLanguageProcessor):
    """
    Telugu language processor for grocery orders
    """
    
    def __init__(self):
        super().__init__("telugu")
    
    def load_vocabulary(self) -> Dict[str, str]:
        """
        Load Telugu grocery vocabulary
        """
        vocabulary = {
            # Vegetables
            'టమాటో': 'tomato',
            'ఉల్లిపాయ': 'onion',
            'వెల్లుల్లి': 'garlic',
            'అల్లం': 'ginger',
            'వంకాయ': 'brinjal',
            'బీన్స్': 'beans',
            'క్యారెట్': 'carrot',
            'బంగాళాదుంప': 'potato',
            'కాలిఫ్లవర్': 'cauliflower',
            'కాబేజీ': 'cabbage',
            'బీరకాయ': 'ridge gourd',
            'గుమ్మడికాయ': 'pumpkin',
            'బెండకాయ': 'okra',
            'పాలకూర': 'spinach',
            'మిర్చి': 'chili',
            'కరివేపాకు': 'curry leaves',
            'కొత్తిమీర': 'coriander',
            'పుదీనా': 'mint',
            
            # Fruits
            'ఆపిల్': 'apple',
            'అరటిపండు': 'banana',
            'నారింజ': 'orange',
            'ద్రాక్ష': 'grapes',
            'మామిడిపండు': 'mango',
            'బొప్పాయి': 'papaya',
            'అనాసపండు': 'pineapple',
            'నిమ్మకాయ': 'lemon',
            'ఉసిరికాయ': 'gooseberry',
            'దానిమ్మ': 'pomegranate',
            
            # Grains & Pulses
            'బియ్యం': 'rice',
            'గోధుమ': 'wheat',
            'కందిపప్పు': 'toor dal',
            'పసరుపప్పు': 'moong dal',
            'మినుముల్లు': 'urad dal',
            'శనగపప్పు': 'chana dal',
            'అట్లు': 'poha',
            'రవ్వ': 'semolina',
            'సోంపు': 'fennel',
            'కొబ్బరి': 'coconut',
            'మిరియాలు': 'pepper',
            'జీలకర్ర': 'cumin',
            'పసుపు': 'turmeric',
            'ధనియాలు': 'coriander seeds',
            
            # Dairy & Proteins
            'పాలు': 'milk',
            'పెరుగు': 'yogurt',
            'వెన్న': 'butter',
            'నెయ్యి': 'ghee',
            'పన్నీర్': 'paneer',
            'గుడ్డు': 'egg',
            'కోడిమాంసం': 'chicken',
            'చేప': 'fish',
            'మాంసం': 'meat',
            
            # Groceries
            'ఉప్పు': 'salt',
            'చక్కెర': 'sugar',
            'నూనె': 'oil',
            'టీ': 'tea',
            'కాఫీ': 'coffee',
            'బిస్కట్': 'biscuit',
            'జామ్': 'jam',
            'తేనె': 'honey',
            'ఎండుద్రాక్ష': 'raisins',
            'బాదంపప్పు': 'almonds',
            'జీడిపప్పు': 'cashew',
            'పిస్తా': 'pistachios'
        }
        
        # Load additional vocabulary from JSON if available
        json_vocab = self.load_json_data("vocabulary.json")
        vocabulary.update(json_vocab)
        
        return vocabulary
    
    def load_units_mapping(self) -> Dict[str, str]:
        """
        Load Telugu units mapping
        """
        units = {
            'కిలో': 'kg',
            'కిలోగ్రాం': 'kg',
            'గ్రాం': 'gram',
            'లీటర్': 'liter',
            'ప్యాకెట్': 'packet',
            'పొట్టలం': 'packet',
            'ముక్క': 'piece',
            'ముక్కలు': 'pieces',
            'డజను': 'dozen',
            'కట్ట': 'bundle',
            'గుత్తి': 'bundle',
            'కప్పు': 'cup',
            'ప్లేట్': 'plate',
            'పాత్ర': 'container',
            'సంచి': 'bag',
            'చిన్నసంచి': 'small bag'
        }
        
        # Load additional units from JSON if available
        json_units = self.load_json_data("units.json")
        units.update(json_units)
        
        return units
    
    def load_numbers_mapping(self) -> Dict[str, str]:
        """
        Load Telugu numbers mapping
        """
        numbers = {
            'ఒకటి': '1',
            'రెండు': '2',
            'మూడు': '3',
            'నాలుగు': '4',
            'ఐదు': '5',
            'ఆరు': '6',
            'ఏడు': '7',
            'ఎనిమిది': '8',
            'తొమ్మిది': '9',
            'పది': '10',
            'పదకొండు': '11',
            'పన్నెండు': '12',
            'పదమూడు': '13',
            'పద్నాలుగు': '14',
            'పదిహేను': '15',
            'పదారు': '16',
            'పదిహేడు': '17',
            'పద్దెనిమిది': '18',
            'పదొమ్మిది': '19',
            'ఇరవై': '20',
            'ఇరవైకొండు': '21',
            'ముప్పై': '30',
            'నలభై': '40',
            'యాభై': '50',
            'అరవై': '60',
            'డెబ్బై': '70',
            'ఎనభై': '80',
            'తొంభై': '90',
            'వంద': '100',
            'వేయి': '1000',
            'సగం': '0.5',
            'పావు': '0.25',
            'ముపావు': '0.75',
            'సగంకిలో': '0.5',
            'పావుకిలో': '0.25',
            'ముపావుకిలో': '0.75'
        }
        
        # Load additional numbers from JSON if available
        json_numbers = self.load_json_data("numbers.json")
        numbers.update(json_numbers)
        
        return numbers
    
    def detect_language_confidence(self, text: str) -> float:
        """
        Calculate confidence score for Telugu language detection
        """
        # Telugu Unicode range
        telugu_chars = set()
        for char in text:
            if '\u0C00' <= char <= '\u0C7F':  # Telugu Unicode block
                telugu_chars.add(char)
        
        # Calculate confidence based on Telugu characters
        total_chars = len([c for c in text if c.isalpha()])
        if total_chars == 0:
            return 0.0
        
        telugu_ratio = len(telugu_chars) / total_chars
        
        # Boost confidence if Telugu-specific words are found
        telugu_indicators = ['చెప్పండి', 'కావాలి', 'తెచ్చి', 'ఇవ్వండి', 'టమాటో', 'ఉల్లిపాయ', 'బియ్యం']
        indicator_count = sum(1 for indicator in telugu_indicators if indicator in text)
        
        # Final confidence calculation
        confidence = telugu_ratio * 0.7 + (indicator_count / len(telugu_indicators)) * 0.3
        
        return min(confidence, 1.0)
    
    def segment_text(self, text: str) -> List[str]:
        """
        Telugu-specific text segmentation
        """
        # Telugu-specific separators
        separators = [',', 'మరియు', 'కూడా', 'వేరు', 'ఇంకా', 'అదనంగా', 'and', 'also']
        
        # Create regex pattern for separators
        separator_pattern = '|'.join(re.escape(sep) for sep in separators)
        
        # Split text
        segments = re.split(separator_pattern, text, flags=re.IGNORECASE)
        
        # Clean and filter segments
        cleaned_segments = [seg.strip() for seg in segments if seg.strip()]
        
        return cleaned_segments
    
    def normalize_text(self, text: str) -> str:
        """
        Telugu-specific text normalization
        """
        # Base normalization
        text = super().normalize_text(text)
        
        # Telugu-specific normalization
        # Remove common Telugu particles and suffixes
        text = re.sub(r'(ని|ను|లు|లను|కు|తో|లో|న|గా)', '', text)
        
        # Normalize common variations
        text = text.replace('్', '')  # Remove virama
        
        return text
    
    def find_grocery_item_in_text(self, text: str) -> str:
        """
        Telugu-specific grocery item finding with fuzzy matching
        """
        # First try exact matching
        result = super().find_grocery_item_in_text(text)
        if result:
            return result
        
        # Telugu-specific fuzzy matching
        words = text.split()
        
        for local_name, english_name in self.vocabulary.items():
            # Check if any word contains the Telugu grocery name
            for word in words:
                # Remove common Telugu suffixes for better matching
                clean_word = re.sub(r'(ని|ను|లు|లను|కు|తో|లో|న|గా)', '', word)
                clean_local = re.sub(r'(ని|ను|లు|లను|కు|తో|లో|న|గా)', '', local_name)
                
                if clean_local in clean_word or clean_word in clean_local:
                    return english_name
                
                # Check for partial matches (at least 70% similarity)
                if len(clean_local) > 3 and len(clean_word) > 3:
                    common_chars = set(clean_local) & set(clean_word)
                    similarity = len(common_chars) / max(len(set(clean_local)), len(set(clean_word)))
                    if similarity >= 0.7:
                        return english_name
        
        return None