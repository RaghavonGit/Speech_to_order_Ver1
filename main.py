#!/usr/bin/env python3
"""
Main Speech-to-Text Grocery Order System
Supports multiple South Indian languages with modular architecture
"""

import re
import sys
import speech_recognition as sr
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
from pydub import AudioSegment

# Import language modules
from tamil_processor import TamilProcessor
from telugu_processor import TeluguProcessor
from veg_processor import VegProcessor
from nonveg_processor import NonVegProcessor

@dataclass
class GroceryItem:
    name: str
    quantity: str
    unit: str
    confidence: float
    instructions: List[str] = None 

@dataclass
class OrderResult:
    items: List[GroceryItem]
    language_detected: str
    raw_text: str
    confidence: float

class SpeechToTextGrocerySystem:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        # Initialize language processors
        self.processors = {
            'tamil': {
                'veg': VegProcessor(),
                'nonveg': NonVegProcessor()
            },
            'telugu': TeluguProcessor()
        }
        
        # Initialize language detectors
        self.language_detectors = {
            'tamil': TamilProcessor(),
            'telugu': TeluguProcessor()
        }
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("System initialized.")

    def build_english_summary(self, items):
        lines = []
        for item in items:
            qty = item.quantity
            unit = item.unit or "units"
            name = item.name
            if getattr(item, "instructions", None):
                instr = ", ".join(item.instructions)
                lines.append(f"{qty} {unit} {name} ({instr})")
            else:
                lines.append(f"{qty} {unit} {name}")
        return ", ".join(lines)

    def detect_language(self, text: str) -> str:
        confidence_scores = {}
        for lang, detector in self.language_detectors.items():
            score = detector.detect_language_confidence(text)
            confidence_scores[lang] = score
        
        detected_lang = max(confidence_scores, key=lambda k: confidence_scores[k])
        self.logger.info(f"Language detected: {detected_lang} with confidence: {confidence_scores[detected_lang]}")
        return detected_lang
    
    def _enter_pressed(self) -> bool:
        try:
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                return key == b'\r'
        except ImportError:
            import sys
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
                return True
        return False

    def record_audio(self) -> Optional[str]:
        collected_text = []
        print("\nSpeak your grocery order.")
        print("Press ENTER when finished.\n")

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.7)
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_threshold = 0.3

            while True:
                try:
                    print("Listening...", end="\r")
                    audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=7)

                    for lang in ["ta-IN", "te-IN", "en-IN"]:
                        try:
                            text = self.recognizer.recognize_google(audio, language=lang)
                            print(f"\nHeard ({lang}): {text}")
                            collected_text.append(text)
                            break
                        except sr.UnknownValueError:
                            continue
                except sr.WaitTimeoutError:
                    pass

                if self._enter_pressed():
                    break

        final_text = " ".join(collected_text).strip()
        return final_text if final_text else None

    def format_order_list(self, order_result: OrderResult) -> Dict:
        formatted_order = {
            "order_id": f"ORDER_{abs(hash(order_result.raw_text)) % 10000:04d}",
            "language_detected": order_result.language_detected,
            "raw_input": order_result.raw_text,
            "confidence": order_result.confidence,
            "items": []
        }
        
        if order_result.language_detected == 'tamil':
            try:
                summary = self.build_english_summary(order_result.items)
                formatted_order["translated_text"] = summary
            except Exception as e:
                self.logger.error(f"Summary generation failed: {e}")
                formatted_order["translated_text"] = ""
        else:
            formatted_order["translated_text"] = ""

        for item in order_result.items:
            formatted_order["items"].append({
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": item.confidence,
                "instructions": getattr(item, "instructions", [])
            })
        return formatted_order

    def split_on_revisions(self, text: str) -> List[str]:
        # Clean text: Remove dots but KEEP COMMAS for list separation
        text = re.sub(r'[.!?…]+', ' ', text)
        text = re.sub(r"\s+", " ", text)
        
        markers = [
            "instead", "no no", "never mind", "cancel", "change", "remove", 
            "actually", "sorry", "wait", "don't want", "replace",
            "அதற்கு பதிலாக", "மாற்று", "நீக்கு",
            "maathu", "mathu", "maathiru", "maathidunga", 
            "badhila", "pathila", "badhulu", "vera", "veru",
            "illa illa", "illa", "illai", 
            "இல்ல இல்ல", "இல்ல", "இல்லை", "வேண்டாம்", "வேணாம்",
            "podaadha", "podaatheenga", "podatheenga", 
            "eduthuru", "eduthudunga", "eduthu", "thappa", "thappu",
            "சேஞ்ச்", "மாத்திடுங்க", "மாத்து", "வேற", "பதிலா"
        ]
        
        segments = []
        buffer = ""
        words = text.split()
        i = 0
        while i < len(words):
            word = words[i]
            marker_found = False
            for marker in markers:
                marker_words = marker.split()
                if i + len(marker_words) <= len(words):
                    current_slice = [w.lower() for w in words[i:i+len(marker_words)]]
                    marker_slice = [mw.lower() for mw in marker_words]
                    
                    if current_slice == marker_slice:
                        if buffer.strip():
                            segments.append(buffer.strip())
                            buffer = ""
                        buffer = " ".join(words[i:i+len(marker_words)])
                        i += len(marker_words)
                        marker_found = True
                        break
            if not marker_found:
                buffer += " " + word
                i += 1
                
        if buffer.strip():
            segments.append(buffer.strip())
        return segments

    def is_cancel_segment(self, segment: str) -> bool:
        segment = segment.lower()
        instruction_exceptions = [
            "bone vendaam", "elumbu vendaam", "tholi vendaam", "skin vendaam",
            "thalai vendaam", "head vendaam", "elumbu illa", "bone illa"
        ]
        for exc in instruction_exceptions:
            if exc in segment:
                temp_seg = segment.replace(exc, "")
                if not any(k in temp_seg for k in ["vendaam", "cancel", "remove", "neekku", "illa", "venam"]):
                    return False

        cancel_keywords = [
            "cancel", "remove", "delete", "don't want", "no need", "not that",
            "no no", "never mind", 
            "வேண்டாம்", "நீக்கு", "இல்லை", "இல்ல", "வேணாம்",
            "venam", "vendaam", "vendam", "podaadha", "podaatheenga", 
            "podatheenga", "eduthuru", "eduthudunga", "eduthu", "edunga", 
            "thappa", "thappu"
        ]
        return any(keyword in segment for keyword in cancel_keywords)

    def is_replace_segment(self, segment: str) -> bool:
        segment = segment.lower()
        replace_keywords = [
            "instead", "replace", "change", "make it", "swap",
            "அதற்கு பதிலாக", "மாற்று", "வேற", 
            "badhila", "pathila", "badhulu", "maathu", "mathu", 
            "maathiru", "maathidunga", "vera", "veru",
            "சேஞ்ச்", "மாத்திடுங்க", "மாத்து", "பதிலா", "அதற்கு பதிலா"
        ]
        return any(keyword in segment for keyword in replace_keywords)

    def segment_has_quantity(self, segment: str) -> bool:
        quantity_patterns = [
            r"\d+", r"அரை", r"கால்", r"முக்கால்", r"கிலோ", r"kg",
            r"பாக்கெட்", r"packet", r"லிட்டர்", r"liter"
        ]
        return any(re.search(p, segment.lower()) for p in quantity_patterns)

    def process_text_input(self, text: str) -> OrderResult:
        order_items: List[GroceryItem] = []
        last_item: Optional[GroceryItem] = None
        last_action_was_cancel = False 

        if not text:
            return OrderResult([], "unknown", "", 0.0)

        detected_lang = self.detect_language(text)
        default_processor = self.processors["tamil"]["veg"] if detected_lang == "tamil" else self.processors.get(detected_lang)
        revision_segments = self.split_on_revisions(text)

        for rev_segment in revision_segments:
            rev_segment = rev_segment.strip()
            if not rev_segment: continue

            target_name_to_block = None

            # 1️⃣ CANCEL CHECK
            if self.is_cancel_segment(rev_segment):
                item_to_remove_index = -1
                cancel_target_items = []
                
                procs = [self.processors["tamil"]["veg"], self.processors["tamil"]["nonveg"]] if detected_lang == "tamil" else [default_processor]
                
                for p in procs:
                    if p:
                        found = p.extract_grocery_items(rev_segment)
                        if found: cancel_target_items.extend(found)
                
                if cancel_target_items:
                    raw_target = cancel_target_items[0]
                    target_name_to_block = raw_target.get("name") if isinstance(raw_target, dict) else raw_target.name
                    if order_items:
                        for idx in range(len(order_items) - 1, -1, -1):
                            if order_items[idx].name == target_name_to_block:
                                item_to_remove_index = idx
                                break
                elif order_items:
                    item_to_remove_index = len(order_items) - 1
                    target_name_to_block = order_items[item_to_remove_index].name

                if item_to_remove_index != -1:
                    removed = order_items.pop(item_to_remove_index)
                    print(f"Removed item: {removed.name}")
                    last_action_was_cancel = True
                else:
                    last_action_was_cancel = False

            # 2️⃣ EXTRACT NEW ITEMS
            processors_to_run = []
            if detected_lang == "tamil":
                processors_to_run.append(self.processors["tamil"]["veg"])
                processors_to_run.append(self.processors["tamil"]["nonveg"])
            elif default_processor:
                processors_to_run.append(default_processor)

            sub_segments = [rev_segment]
            if processors_to_run and hasattr(processors_to_run[0], 'segment_text'):
                sub_segments = processors_to_run[0].segment_text(rev_segment)

            for item_segment in sub_segments:
                for proc in processors_to_run:
                    if hasattr(proc, 'normalize_numbers'):
                        item_segment = proc.normalize_numbers(item_segment)

                extracted_group = []
                for proc in processors_to_run:
                    found = proc.extract_grocery_items(item_segment)
                    if found: extracted_group.extend(found)

                # PRE-CHECK: Remove item if overlapping with Replacement intent
                if self.is_replace_segment(rev_segment) and extracted_group:
                    for raw_item in extracted_group:
                        name = raw_item.get("name") if isinstance(raw_item, dict) else raw_item.name
                        for i, existing in enumerate(order_items):
                            if existing.name == name:
                                order_items.pop(i)
                                break

                for raw_item in extracted_group:
                    if isinstance(raw_item, dict):
                        item = GroceryItem(
                            name=raw_item.get("name", ""),
                            quantity=raw_item.get("quantity", ""),
                            unit=raw_item.get("unit", ""),
                            confidence=raw_item.get("confidence", 0.0),
                            instructions=raw_item.get("instructions", [])
                        )
                    else:
                        item = raw_item

                    if target_name_to_block and item.name == target_name_to_block:
                        continue
                    
                    # REPLACE LOGIC
                    if self.is_replace_segment(rev_segment) and order_items:
                        if not last_action_was_cancel:
                            prev = order_items.pop()
                            if not self.segment_has_quantity(rev_segment):
                                item.quantity = prev.quantity
                                item.unit = prev.unit
                        
                        order_items.append(item)
                        last_action_was_cancel = False
                        continue

                    # UPDATE LOGIC
                    replaced = False
                    for i, existing in enumerate(order_items):
                        if existing.name == item.name:
                            if item.quantity and item.quantity != "1": 
                                existing.quantity = item.quantity
                                existing.unit = item.unit
                            if item.instructions:
                                if existing.instructions is None: existing.instructions = []
                                existing.instructions.extend(x for x in item.instructions if x not in existing.instructions)
                            order_items[i] = existing
                            replaced = True
                            break
                    
                    # ADD LOGIC
                    if not replaced:
                        order_items.append(item)
                        last_action_was_cancel = False

        avg_confidence = (sum(i.confidence for i in order_items) / len(order_items) if order_items else 0.0)
        return OrderResult(order_items, detected_lang, text, round(avg_confidence, 2))

    def save_order(self, order: Dict, filename: str = None) -> str:
        if not filename:
            filename = f"order_{order['order_id']}.json"
        filepath = Path("orders") / filename
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(order, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Order saved to {filepath}")
        return str(filepath)

    def process_audio_file(self, file_path: str) -> Optional[OrderResult]:
        original_file_path = file_path
        temp_wav = None
        try:
            if file_path.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(file_path)
                temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                audio.export(temp_wav_file.name, format='wav')
                temp_wav = temp_wav_file.name
                file_path = temp_wav
            
            with sr.AudioFile(file_path) as source:
                audio = self.recognizer.record(source)
            self.logger.info(f"Processing audio file: {original_file_path}")
            
            text = None
            for lang_code in ['ta-IN', 'te-IN', 'en-IN']:
                try:
                    text = self.recognizer.recognize_google(audio, language=lang_code)
                    break
                except sr.UnknownValueError: continue
            
            self.logger.info(f"Recognized text from file: {text}")
            if text is None: return None
            return self.process_text_input(text)
        except Exception as e:
            self.logger.error(f"Error processing audio file: {e}")
            return None
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except: pass

    def process_voice_order(self) -> Optional[OrderResult]:
        self.logger.info("Starting voice order capture")
        text = self.record_audio()
        if not text:
            self.logger.error("No speech detected")
            return None
        self.logger.info(f"Final recognized speech: {text}")
        return self.process_text_input(text)

def main():
    system = SpeechToTextGrocerySystem()
    sample_files_dir = os.path.join(os.path.dirname(__file__), 'Sample Files')
    if not os.path.exists(sample_files_dir):
        os.makedirs(sample_files_dir, exist_ok=True)

    print("South Indian Languages Grocery Order System")
    print("Supported languages: Tamil, Telugu")
    print("\nChoose input method:")
    print("1. Voice input")
    print("2. Text input")
    print("3. Audio file input")

    choice = input("Enter choice (1, 2 or 3): ").strip()

    result = None
    if choice == "1":
        result = system.process_voice_order()
    elif choice == "2":
        text = input("\nEnter your grocery order: ")
        result = system.process_text_input(text)
    elif choice == "3":
        try:
            files = [f for f in os.listdir(sample_files_dir) if f.lower().endswith(('.wav', '.flac', '.mp3'))]
        except Exception: files = []
        
        if not files:
            print("No audio files found in 'Sample Files' folder.")
            return
        for idx, fname in enumerate(files, 1):
            print(f"{idx}. {fname}")
        try:
            idx = int(input("Select file number: ")) - 1
            if 0 <= idx < len(files):
                result = system.process_audio_file(os.path.join(sample_files_dir, files[idx]))
        except ValueError:
            print("Invalid input")
    
    if result:
        formatted_order = system.format_order_list(result)
        print(f"\n--- ORDER PROCESSED ---")
        print(f"Language: {formatted_order['language_detected']}")
        print(f"Items Found: {len(formatted_order['items'])}")
        for item in formatted_order['items']:
            print(f"- {item['name']}: {item['quantity']} {item['unit']} ({item['confidence']})")
        system.save_order(formatted_order)

if __name__ == "__main__":
    main()