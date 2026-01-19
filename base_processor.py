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
    instructions: List[str] = None # Added default None to match main.py expectations

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
        text = re.sub(r'\s+', ' ', text.strip())
        text = text.lower()
        return text

    # --- NEW METHOD: Required by main.py ---
    def segment_text(self, text: str) -> List[str]:
        """
        Splits text into sub-segments based on conjunctions (and, comma, etc.)
        This is crucial for handling multiple items in one sentence.
        """
        # Default splitting by common separators. 
        # Child classes (like TeluguProcessor) can override this with language-specific conjunctions.
        segments = re.split(r'[,;]|\s+and\s+|\s+mattrum\s+|\s+mariya\s+', text)
        return [s.strip() for s in segments if s.strip()]

    # --- NEW METHOD: Required by main.py ---
    def normalize_numbers(self, text: str) -> str:
        """
        Convert local language numbers to digits in the text string.
        """
        words = text.split()
        for i, word in enumerate(words):
            # Check numbers map (loaded from child class)
            if word in self.numbers_map:
                words[i] = self.numbers_map[word]
        return " ".join(words)
    
    def compute_item_confidence(
            self,
            language_conf:float,
            vocab_conf:float,
            qty_conf:float,
            context_conf:float
        )-> float:
        return round(
            0.35*language_conf+
            0.35*vocab_conf+
            0.2*qty_conf+
            0.1*context_conf, 2
        )
    
    def extract_quantities_and_units(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract quantity-unit pairs from text
        Returns list of (quantity, unit, remaining_text) tuples
        """
        results = []
        
        # Regex to find digits followed by units
        # Updated to include units from the loaded units_map keys
        unit_keys = "|".join([re.escape(k) for k in self.units_map.keys()] + ['kg', 'g', 'l', 'ml', 'pcs'])
        pattern = fr'(\d+(?:\.\d+)?)\s*({unit_keys}|kg|kilogram|kilo|g|gram|liter|litre|packet|packets|piece|pieces)'
        
        matches = re.finditer(pattern, text)
        for match in matches:
            quantity_raw = match.group(1)
            unit_raw = match.group(2)
            
            # Convert local units to English
            unit = self.convert_unit_to_english(unit_raw)
            
            if quantity_raw and unit:
                # Basic logic to identify text part; usually refined in process_segment
                remaining_text = text # Simplified for this base implementation
                results.append((quantity_raw, unit, remaining_text))
        
        return results
    
    def convert_unit_to_english(self, unit_text: str) -> Optional[str]:
        if unit_text in self.units_map:
            return self.units_map[unit_text]
        
        english_units = ['kg', 'gram', 'grams', 'liter', 'liters', 'piece', 'pieces', 'dozen', 'packet', 'packets']
        if unit_text.lower() in english_units:
            return unit_text.lower()
        return None
    
    def extract_grocery_items(self, text: str) -> List[GroceryItem]:
        """
        Main method to extract grocery items from text
        UPDATED: Supports finding multiple items in one string
        """
        text = self.normalize_text(text)
        text = self.normalize_numbers(text) # Use the new normalizer
        
        items = []
        
        # 1. Try to split by segment_text first
        segments = self.segment_text(text)
        
        for seg in segments:
            item = self.process_segment(seg)
            if item:
                items.append(item)
            else:
                # Fallback: iterative search if segmentation failed but vocab match exists
                # (Simple greedy match logic)
                for local_name, english_name in self.vocabulary.items():
                    if local_name in seg:
                        # Check if we already found this
                        if not any(i.name == english_name for i in items):
                            # Try to find quantity nearby
                            # For now, default to 1 unit if not explicitly found via process_segment
                            items.append(GroceryItem(
                                name=english_name,
                                quantity="1",
                                unit="units",
                                confidence=0.6
                            ))

        return items
    
    def process_segment(self, segment: str) -> Optional[GroceryItem]:
        """
        Process individual segment to extract grocery item
        """
        qty_unit_pairs = self.extract_quantities_and_units(segment)
        
        quantity = "1"
        unit = "units"
        
        if qty_unit_pairs:
            quantity, unit, _ = qty_unit_pairs[0]
        
        # Find item name
        item_name = self.find_grocery_item_in_text(segment)
        
        if item_name:
            return GroceryItem(
                name=item_name,
                quantity=quantity,
                unit=unit,
                confidence=self.compute_item_confidence(
                    language_conf=self.detect_language_confidence(segment),
                    vocab_conf=1,
                    qty_conf=1 if qty_unit_pairs else 0.6,
                    context_conf=1.0
                )
            )
        return None
    
    def find_grocery_item_in_text(self, text: str) -> Optional[str]:
        words = text.split()
        
        # Exact matches
        for local_name, english_name in self.vocabulary.items():
            if local_name in text:
                return english_name
        
        # Partial matches
        for local_name, english_name in self.vocabulary.items():
            for word in words:
                if local_name in word or word in local_name:
                    return english_name
        return None
    
    def load_json_data(self, filename: str) -> Dict:
        try:
            # Assumes data folder exists relative to this script
            filepath = Path(__file__).parent / "data" / self.language_name / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
        return {}