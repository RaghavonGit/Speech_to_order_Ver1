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
import speech_recognition as sr
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from transformers import PreTrainedTokenizer
from typing import Optional

# Audio Processing
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence

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
        self.translator_tokenizer: Optional[PreTrainedTokenizer] = None
        # 1. Initialize Extraction Processors
        self.processors = {
            'tamil': {'veg': VegProcessor(), 'nonveg': NonVegProcessor()},
            'telugu': TeluguProcessor()
        }
        self.language_detectors = {
            'tamil': TamilProcessor(),
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

    # =========================================================================
    # AUDIO PIPELINE
    # =========================================================================
    
    def preprocess_audio(self, audio_segment: AudioSegment) -> AudioSegment:
        """Normalize audio volume and format for Speech Recognition"""
        normalized = effects.normalize(audio_segment)
        normalized = normalized.set_channels(1)
        normalized = normalized.set_frame_rate(16000)
        return normalized

    def process_audio_file(self, file_path: str) -> Optional[OrderResult]:
        logger.info(f"Processing audio: {file_path}")
        if not os.path.exists(file_path):
            logger.error("File not found.")
            return None

        temp_dir = tempfile.mkdtemp()
        full_transcript = []

        try:
            # 1. Load & Clean
            raw_audio = AudioSegment.from_file(file_path)
            audio = self.preprocess_audio(raw_audio)
            
            # 2. Smart Chunking (Fixes Google Timeout on Long Files)
            chunks = split_on_silence(
                audio, min_silence_len=700, silence_thresh=audio.dBFS - 14, keep_silence=500
            )
            if not chunks: chunks = [audio]
            if not chunks or all(len(c)<1000 for c in chunks):
                logger.error("No valid audio chunks found.")
                return None

            # 3. Transcribe Chunks
            for i, chunk in enumerate(chunks):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                chunk.export(chunk_path, format="wav")
                
                with sr.AudioFile(chunk_path) as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = self.recognizer.record(source)
                    
                    # Try Tamil first, then English
                    text_chunk = None
                    try:
                        text_chunk = self.recognizer.recognize_google(audio_data, language='ta-IN')
                    except sr.UnknownValueError:
                        try:
                            text_chunk = self.recognizer.recognize_google(audio_data, language='en-IN')
                        except sr.UnknownValueError:
                            text_chunk = None
                    
                    if not text_chunk:
                        logger.warning("Stt recognition failed for chunk.")
                        try:
                            text_chunk = self.recognizer.recognize_google(audio_data, language='en-IN')
                        except:
                            text_chunk=None

            final_text = " ".join(full_transcript).strip()
            logger.info(f"Final Transcript: {final_text}")
            
            if not final_text: return None
            return self.process_text_input(final_text)

        except Exception as e:
            logger.error(f"Audio Processing Error: {e}")
            return None
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

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
            clean_text = self.processors['tamil']['nonveg'].normalize_numbers(clean_text)
        
        # 3. Select processors
        # We use Tamil processors for both because they contain the full English+Tamil vocab maps
        active_processors = [self.processors['tamil']['veg'], self.processors['tamil']['nonveg']]
        if detected_lang == 'tamil' or 'chicken' in clean_text or 'mutton' in clean_text:
            active_processors.append(self.processors['tamil']['nonveg'])

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