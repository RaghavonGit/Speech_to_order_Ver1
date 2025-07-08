#!/usr/bin/env python3
"""
Base Language Processor
Abstract base class for all language processors
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
import json
from pathlib import Path

@dataclass
class GroceryItem:
    name: str
    quantity: str
    unit: str
    confidence: float

class BaseLanguageProcessor(ABC):
    """
    Abstract base class for language-specific processors
    """
    
    def __init__(self, language_name: str):
        self.language_name = language_name
        self.vocabulary = self.load_vocabulary()
        self.units_map = self.load_units_mapping()
        self.numbers_map = self.load_numbers_mapping()
    
    @abstractmethod
    def load_vocabulary(self) -> Dict[str, str]:
        """Load language-specific grocery vocabulary"""
        pass
    
    @abstractmethod
    def load_units_mapping(self) -> Dict[str, str]:
        """Load units mapping (local units to English)"""
        pass
    
    @abstractmethod
    def load_numbers_mapping(self) -> Dict[str, str]:
        """Load numbers mapping (local numbers to English)"""
        pass
    
    @abstractmethod
    def detect_language_confidence(self, text: str) -> float:
        """Calculate confidence score for language detection"""
        pass
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for processing
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Convert to lowercase for processing
        text = text.lower()
        
        return text
    
    def extract_quantities_and_units(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract quantity-unit pairs from text
        Returns list of (quantity, unit, remaining_text) tuples
        """
        results = []
        
        # Common patterns for quantity extraction
        patterns = [
            r'(\d+\.?\d*)\s*(\w+)',  # Number followed by unit
            r'(\w+)\s*(\w+)',        # Word followed by unit (for text numbers)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                quantity_raw = match.group(1)
                unit_raw = match.group(2)
                
                # Convert local numbers to English
                quantity = self.convert_number_to_english(quantity_raw)
                
                # Convert local units to English
                unit = self.convert_unit_to_english(unit_raw)
                
                if quantity and unit:
                    # Remove matched text
                    remaining_text = text.replace(match.group(0), '', 1).strip()
                    results.append((quantity, unit, remaining_text))
        
        return results
    
    def convert_number_to_english(self, number_text: str) -> Optional[str]:
        """
        Convert local language numbers to English
        """
        # If already a digit, return as is
        if number_text.replace('.', '').isdigit():
            return number_text
        
        # Check in numbers mapping
        if number_text in self.numbers_map:
            return self.numbers_map[number_text]
        
        return None
    
    def convert_unit_to_english(self, unit_text: str) -> Optional[str]:
        """
        Convert local language units to English
        """
        if unit_text in self.units_map:
            return self.units_map[unit_text]
        
        # If already in English, return as is
        english_units = ['kg', 'gram', 'grams', 'liter', 'liters', 'piece', 'pieces', 'dozen', 'packet', 'packets']
        if unit_text.lower() in english_units:
            return unit_text.lower()
        
        return None
    
    def extract_grocery_items(self, text: str) -> List[GroceryItem]:
        """
        Main method to extract grocery items from text
        """
        text = self.normalize_text(text)
        items = []
        
        # Split text into potential item segments
        segments = self.segment_text(text)
        
        for segment in segments:
            item = self.process_segment(segment)
            if item:
                items.append(item)
        
        return items
    
    def segment_text(self, text: str) -> List[str]:
        """
        Segment text into individual item descriptions
        """
        # Common separators
        separators = [',', 'மற்றும்', 'और', 'ಮತ್ತು', 'ഒപ്പം', 'and', 'also']
        
        # Create regex pattern for separators
        separator_pattern = '|'.join(re.escape(sep) for sep in separators)
        
        # Split text
        segments = re.split(separator_pattern, text, flags=re.IGNORECASE)
        
        # Clean and filter segments
        cleaned_segments = [seg.strip() for seg in segments if seg.strip()]
        
        return cleaned_segments
    
    def process_segment(self, segment: str) -> Optional[GroceryItem]:
        """
        Process individual segment to extract grocery item
        """
        # Extract quantities and units
        qty_unit_pairs = self.extract_quantities_and_units(segment)
        
        if not qty_unit_pairs:
            # Try to find item without explicit quantity
            item_name = self.find_grocery_item_in_text(segment)
            if item_name:
                return GroceryItem(
                    name=item_name,
                    quantity="1",
                    unit="piece",
                    confidence=0.6
                )
            return None
        
        # Use the first quantity-unit pair found
        quantity, unit, remaining_text = qty_unit_pairs[0]
        
        # Find grocery item name in remaining text or original segment
        item_name = self.find_grocery_item_in_text(remaining_text) or self.find_grocery_item_in_text(segment)
        
        if item_name:
            return GroceryItem(
                name=item_name,
                quantity=quantity,
                unit=unit,
                confidence=0.8
            )
        
        return None
    
    def find_grocery_item_in_text(self, text: str) -> Optional[str]:
        """
        Find grocery item name in text using vocabulary
        """
        words = text.split()
        
        # Check for exact matches first
        for local_name, english_name in self.vocabulary.items():
            if local_name in text:
                return english_name
        
        # Check for partial matches
        for local_name, english_name in self.vocabulary.items():
            for word in words:
                if local_name in word or word in local_name:
                    return english_name
        
        return None
    
    def load_json_data(self, filename: str) -> Dict:
        """
        Load data from JSON file
        """
        try:
            filepath = Path(f"data/{self.language_name}/{filename}")
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
        
        return {}