#!/usr/bin/env python3
"""
BACKEND ENGINE: Handles Audio Processing, Text Extraction, and Translation.
"""

import os
import sys
import re
import json
import time
import logging
import tempfile
import torch
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from transformers import PreTrainedTokenizer
from typing import Optional
import speech_recognition as sr
from pydub import AudioSegment



# Audio Processing

# AI Translation
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Custom Processors
from tamil_processor import TamilProcessor
from telugu_processor import TeluguProcessor
from veg_processor import VegProcessor
from nonveg_processor import NonVegProcessor

# Optimize Torch
torch.backends.cudnn.benchmark = True

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GroceryItem:
    name: str
    quantity: str
    unit: str
    confidence: float
    instructions: list = None

@dataclass
class OrderResult:
    items: List[GroceryItem]
    language_detected: str
    raw_text: str
    confidence: float

class SpeechToTextGrocerySystem:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6
        self.recognizer.phrase_threshold = 0.3
        self.translator_tokenizer: Optional[PreTrainedTokenizer] = None
        # 1. Initialize Extraction Processors
        self.processors = {
            'tamil': {'veg': VegProcessor(), 'nonveg': NonVegProcessor()},
            'telugu': TeluguProcessor()
        }

        # 2. Initialize AI4Bharat Translation Model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.translator_model = None
        self.translator_tokenizer = None
        
        logger.info(f"Loading AI4Bharat Model on {self.device}...")
        try:
            model_name = "ai4bharat/indictrans2-indic-en-dist-200M"
            self.translator_tokenizer = AutoTokenizer.from_pretrained(
                model_name, use_fast=False, trust_remote_code=True
            )
            self.translator_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name, trust_remote_code=True
            ).to(self.device)
            self.translator_model.eval()
            logger.info("✅ Translation Model Loaded.")
        except Exception as e:
            logger.error(f"❌ Failed to load Translation Model: {e}")
            return None

    # =========================================================================
    # AUDIO PIPELINE
    # =========================================================================
    
    def _prepare_audio(self,input_path:str)->str:
        sound= AudioSegment.from_file(input_path)
        sound=sound.set_channels(1)
        sound=sound.set_frame_rate(16000)
        base,_=os.path.splitext(input_path)
        tmp_path=base+"_proc.wav"
        sound.export(tmp_path,format='wav')
        return tmp_path

    def process_audio_file(self, file_path: str) -> Optional[OrderResult]:
        logger.info(f"Processing audio: {file_path}")

        if not os.path.exists(file_path):
            logger.error("File not found.")
            return None

        try:
            wav_path = self._prepare_audio(file_path)

            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)

            text = None

        # 1️⃣ Try Tamil first
            try:
                text = self.recognizer.recognize_google(audio, language="ta-IN")
            except sr.UnknownValueError:
                pass

            # 2️⃣ Fallback to English (code-mix support)
            if not text:
                try:
                    text = self.recognizer.recognize_google(audio, language="en-IN")
                except sr.UnknownValueError:
                    pass
            if not text:
                logger.warning("No speech recognized.")
                return OrderResult([], "unknown", "", 0.0)

            text = re.sub(r"\s+", " ", text).strip()
            logger.info(f"STT Text: {text}")

            return self.process_text_input(text)

        except Exception as e:
            logger.error(f"Audio Processing Error: {e}")
            return None

        
    # =========================================================================
    # TRANSLATION PIPELINE (FIXED)
    # =========================================================================

    def translate_indic_to_english(self, text: str, src_lang: str = 'tam_Taml') -> str:
        """
        Translates text to English. Handles tokenizer NoneType bugs.
        """
        if not self.translator_model or not text.strip():
            return ""

        try:
            # Clean text
            clean_text = text.replace("ஹலோ", "").replace("வணக்கம்", "").strip()
            clean_text = " ".join(clean_text.split())
            
            input_prompt = f"{src_lang} eng_Latn {clean_text}"
            
            # Tokenize
            if self.translator_tokenizer is None:
                return text 
            encoded = self.translator_tokenizer(
                input_prompt, return_tensors='pt', padding=True, truncation=True, max_length=512)
            
            # --- THE FIX IS HERE ---
            # Filter out None values before moving to device (Fixes 'NoneType' object has no attribute 'shape')
            inputs = {k: v.to(self.device)
                      for k,v in encoded.items()
                      if isinstance(v, torch.Tensor)}
            
            with torch.no_grad():
                generated_tokens = self.translator_model.generate(
                    **inputs,
                    max_new_tokens=256,
                    num_beams=5,
                    do_sample=False
                )
            
            decoded = self.translator_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            logger.info(f"Translated: {decoded}")
            return decoded

        except Exception as e:
            logger.error(f"Translation Error: {e}")
            return text

    # =========================================================================
    # EXTRACTION PIPELINE (Regex Logic)
    # =========================================================================

# REPLACE THE process_text_input METHOD IN grocery_system.py WITH THIS:

    def process_text_input(self, text: str) -> OrderResult:
        if not text:
            return OrderResult([], "unknown", "", 0.0)

        # 1. Detect Language
        is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
        detected_lang = 'tamil' if is_tamil else 'english'
        logger.info(f"Processing Text: '{text}' (Detected: {detected_lang})")

        # 2. Normalize text
        # DO NOT remove dots (.) here, it breaks decimal quantities like 1.5kg
        clean_text = text.lower()
        if detected_lang == 'tamil':
            # Only use Tamil specific normalization if Tamil is detected
            clean_text = self.processors['tamil']['veg'].normalize_numbers(clean_text)  
            clean_text = self.processors['tamil']['nonveg'].normalize_numbers(clean_text)
        
        # 3. Select processors
        # We use Tamil processors for both because they contain the full English+Tamil vocab maps
        active_processors = [self.processors['tamil']['veg'], self.processors['tamil']['nonveg']]


        # 4. Segment text (Split "onion and tomato" into ["onion", "tomato"])
        segments = [clean_text]
        if hasattr(self.processors['tamil']['veg'], 'segment_text'):
            segments = self.processors['tamil']['veg'].segment_text(clean_text)

        all_extracted_items = []

        # 5. Extract items from ALL segments
        for segment in segments:
            if not segment.strip():
                continue
             
            # Run all processors on this segment
            veg_items=self.processors['tamil']['veg'].extract_grocery_items(segment)
            if veg_items:
                all_extracted_items.extend(veg_items)
            nonveg_items=self.processors['tamil']['nonveg'].extract_grocery_items(segment)
            if nonveg_items:
                all_extracted_items.extend(nonveg_items)

        # 6. Convert to GroceryItem Objects and Deduplicate
        final_items = []
        # --- FIX: Ensure Egg always treated as non-veg with tray unit ---
        for item in all_extracted_items:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("local_name")
            if name and name.lower() == "egg":
                item["unit"] = "tray"

        for raw_item in all_extracted_items:
            # Handle Dictionary format (from VegProcessor)
            if isinstance(raw_item, dict):
                name = raw_item.get('name') or raw_item.get('local_name')
                qty = raw_item.get('quantity', '1')
                unit = raw_item.get('unit') or '' # Default to units if empty
                conf = raw_item.get('confidence', 0.0)
                instr = raw_item.get('instructions', [])
            else:
                # Handle Object format (from BaseProcessor)
                name = raw_item.name
                qty = raw_item.quantity
                unit = raw_item.unit
                conf = raw_item.confidence
                instr = getattr(raw_item, 'instructions', [])

            new_item = GroceryItem(
                name=name,
                quantity=str(qty), # Ensure string
                unit=unit,
                confidence=conf,
                instructions=instr
            )

            # Check if we already have this item to merge duplicates
            existing_idx = next(
                (i for i, x in enumerate(final_items) if x.name == name),
                None
            )

            if existing_idx is not None:
                # If existing was "1" (default) and new is specific, overwrite it
                if final_items[existing_idx].quantity == "1" and qty != "1":
                    final_items[existing_idx] = new_item
                # Or if units match, you might want to add them (logic simplified here to overwrite)
                # Do NOT overwrite unless quantity is explicit
            else:
                final_items.append(new_item)

        avg_conf = (
            sum(i.confidence for i in final_items) / len(final_items)
            if final_items else 0.0
        )

        logger.info(f"Extracted {len(final_items)} items: {[i.name for i in final_items]}")
        logger.info(f"RAW EXTRACTED ITEMS: {all_extracted_items}")

        return OrderResult(
            items=final_items,
            language_detected=detected_lang,
            raw_text=text,
            confidence=avg_conf
        )

    # =========================================================================
    # UTILS
    # =========================================================================

    def format_order_list(self, result: OrderResult) -> Dict:
        """Formats the result and triggers translation"""
        translated_text = ""
        
        if result.language_detected == 'tamil':
            translated_text = self.translate_indic_to_english(result.raw_text, 'tam_Taml')
        elif result.language_detected == 'telugu':
            translated_text = self.translate_indic_to_english(result.raw_text, 'tel_Tel')
        
        if not translated_text:
            translated_text = result.raw_text

        return {
            "order_id": f"ORDER_{int(time.time())}",
            "language_detected": result.language_detected,
            "raw_input": result.raw_text,
            "translated_text": translated_text,
            "confidence": result.confidence,
            "items": [asdict(i) for i in result.items]
        }

    def save_order(self, order: Dict, filename: str = None) -> str:
        if not filename:
            filename = f"order_{order['order_id']}.json"
        
        filepath = Path("orders") / filename
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(order, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Order saved: {filepath}")
        return str(filepath)