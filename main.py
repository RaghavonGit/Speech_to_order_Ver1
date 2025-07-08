#!/usr/bin/env python3
"""
Main Speech-to-Text Grocery Order System
Supports multiple South Indian languages with modular architecture
"""

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

@dataclass
class OrderResult:
    items: List[GroceryItem]
    language_detected: str
    raw_text: str
    confidence: float

class SpeechToTextGrocerySystem:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # self.microphone = sr.Microphone()
        
        # Initialize language processors for extraction
        self.processors = {
            'tamil': {
                'veg': VegProcessor(),
                'nonveg': NonVegProcessor()
            },
            'telugu': TeluguProcessor()
        }
        # Initialize language detectors for language detection only
        self.language_detectors = {
            'tamil': TamilProcessor(),
            'telugu': TeluguProcessor()
        }
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Translation model and device setup
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Using device: {self.device}")
        self.logger.info("Loading translation model...")
        self.translator_tokenizer = AutoTokenizer.from_pretrained(
            "ai4bharat/indictrans2-indic-en-dist-200M", use_fast=False, trust_remote_code=True
        )
        self.translator_model = AutoModelForSeq2SeqLM.from_pretrained(
            "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True
        ).to(self.device)
        self.logger.info("Translation model loaded.")
        
        # Adjust for ambient noise
        # with self.microphone as source:
        #     self.recognizer.adjust_for_ambient_noise(source)
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text
        Returns the detected language key
        """
        confidence_scores = {}
        for lang, detector in self.language_detectors.items():
            score = detector.detect_language_confidence(text)
            confidence_scores[lang] = score
        # Return language with highest confidence
        detected_lang = max(confidence_scores, key=lambda k: confidence_scores[k])
        self.logger.info(f"Language detected: {detected_lang} with confidence: {confidence_scores[detected_lang]}")
        return detected_lang
    
    def detect_veg_nonveg(self, text: str) -> str:
        """
        Detect if the text is veg or non-veg using Tamil vocabularies.
        Returns 'veg' or 'nonveg'. Defaults to 'veg' if unsure.
        """
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vocab_path = os.path.join(base_dir, 'nonveg_vocab_ta.txt')
        with open(vocab_path, encoding='utf-8') as f:
            nonveg_vocab = set(line.strip() for line in f if line.strip())
        text_lower = text.lower()
        for word in nonveg_vocab:
            if word in text_lower:
                return 'nonveg'
        return 'veg'
    
    def record_audio(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
        """
        Record audio from microphone and convert to text
        """
        try:
            self.logger.info("Listening for grocery order...")
            
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            self.logger.info("Processing audio...")
            
            # Try Google Speech Recognition first (supports multiple languages)
            try:
                text = self.recognizer.recognize_google(audio, language='ta-IN')  # Default to Tamil
                return text
            except sr.UnknownValueError:
                # Try with different language settings
                for lang_code in ['te-IN', 'kn-IN', 'ml-IN', 'en-IN']:
                    try:
                        text = self.recognizer.recognize_google(audio, language=lang_code)
                        return text
                    except sr.UnknownValueError:
                        continue
                
                self.logger.error("Could not understand audio")
                return None
                
        except sr.WaitTimeoutError:
            self.logger.error("Listening timeout")
            return None
        except Exception as e:
            self.logger.error(f"Error recording audio: {e}")
            return None
    
    def process_text_input(self, text: str) -> OrderResult:
        """
        Process text input and extract grocery items
        """
        if text is None:
            return OrderResult(items=[], language_detected="unknown", raw_text="", confidence=0.0)
        # Detect language
        detected_lang = self.detect_language(text)
        # For Tamil, auto-detect veg/non-veg and use the appropriate processor
        if detected_lang == 'tamil':
            category = self.detect_veg_nonveg(text)
            processor = self.processors['tamil'][category]
        else:
            processor = self.processors[detected_lang]
        # Extract grocery items
        items = processor.extract_grocery_items(text)
        # Convert dicts to GroceryItem objects if needed
        grocery_items = []
        for item in items:
            if isinstance(item, dict):
                grocery_items.append(GroceryItem(
                    name=item.get("name", ""),
                    quantity=item.get("quantity", ""),
                    unit=item.get("unit", ""),
                    confidence=item.get("confidence", 0.0)
                ))
            else:
                grocery_items.append(item)
        return OrderResult(
            items=grocery_items,
            language_detected=detected_lang,
            raw_text=text,
            confidence=0.8  # Default confidence
        )
    
    def process_voice_order(self) -> Optional[OrderResult]:
        """
        Main method to process voice order
        """
        # Record audio
        text = self.record_audio()
        
        if not text:
            return None
        
        self.logger.info(f"Recognized text: {text}")
        
        # Process the text
        return self.process_text_input(text)
    
    def format_order_list(self, order_result: OrderResult) -> Dict:
        """
        Format the order result into a structured format
        """
        formatted_order = {
            "order_id": f"ORDER_{hash(order_result.raw_text) % 10000:04d}",
            "language_detected": order_result.language_detected,
            "raw_input": order_result.raw_text,
            "confidence": order_result.confidence,
            "items": []
        }
        # Translate raw_input to English using IndicTrans2
        translated_text = ""
        if order_result.language_detected == 'tamil':
            print("[Main] Translating Tamil text to English...")
            translated_text = self.translate_indic_to_english(order_result.raw_text)
            print(f"[Main] Translated text: {translated_text}")
        formatted_order["translated_text"] = translated_text
        for item in order_result.items:
            formatted_order["items"].append({
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": item.confidence,
                "instructions": getattr(item, "instructions", "")
            })
        return formatted_order
    
    def save_order(self, order: Dict, filename: str = None) -> str:
        """
        Save order to JSON file
        """
        if not filename:
            filename = f"order_{order['order_id']}.json"
        
        filepath = Path("orders") / filename
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(order, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Order saved to {filepath}")
        return str(filepath)

    def process_audio_file(self, file_path: str) -> Optional[OrderResult]:
        """
        Process an audio file and extract grocery items
        """
        # If the file is mp3, convert to wav first
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
            # Try Google Speech Recognition first (supports multiple languages)
            try:
                text = self.recognizer.recognize_google(audio, language='ta-IN')  # Default to Tamil
            except sr.UnknownValueError:
                # Try with different language settings
                text = None
                for lang_code in ['te-IN', 'kn-IN', 'ml-IN', 'en-IN']:
                    try:
                        text = self.recognizer.recognize_google(audio, language=lang_code)
                        break
                    except sr.UnknownValueError:
                        continue
                if text is None:
                    self.logger.error("Could not understand audio in file")
                    return None
            self.logger.info(f"Recognized text from file: {text}")
            if text is None:
                return None
            return self.process_text_input(text)
        except Exception as e:
            self.logger.error(f"Error processing audio file: {e}")
            return None
        finally:
            if temp_wav:
                import os
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

    def translate_indic_to_english(self, text: str, src_lang: str = None) -> str:
        """
        Translate Indic language text to English using IndicTrans2 model.
        Always uses 'tam_Taml' as the source language tag for now.
        """
        src_lang = 'tam_Taml'
        self.logger.info(f"Attempting to translate: '{text}' from source language '{src_lang}'")
        # print(f"Attempting to translate: '{text}' from source language '{src_lang}'")
        try:
            input_text = f"<{src_lang}> {text}"
            # print(f"[DEBUG] input_text : {input_text}")
            self.logger.info(f"Input to tokenizer: '{input_text}'")
            inputs = self.translator_tokenizer(input_text, return_tensors="pt")
            # Move tensors to the correct device
            for k in inputs:
                inputs[k] = inputs[k].to(self.device)
            self.logger.info("Tokenization successful.")

            generated_tokens = self.translator_model.generate(**inputs, max_length=256)
            self.logger.info("Token generation successful.")

            translated_text = self.translator_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
            self.logger.info(f"Decoded translation: '{translated_text}'")
            print(f"[DEBUG] Translated text (from translate_indic_to_english): {translated_text}")
            return translated_text
        except Exception as e:
            self.logger.error(f"Error during translation: {e}", exc_info=True)
            return ""

def main():
    """
    Main function to demonstrate the system
    """
    system = SpeechToTextGrocerySystem()
    import os
    sample_files_dir = os.path.join(os.path.dirname(__file__), 'Sample Files')

    print("South Indian Languages Grocery Order System")
    print("Supported languages: Tamil, Telugu")
    print("\nChoose input method:")
    print("1. Voice input")
    print("2. Text input")
    print("3. Audio file input")

    choice = input("Enter choice (1, 2 or 3): ").strip()

    if choice == "1":
        print("\nSpeak your grocery order now...")
        result = system.process_voice_order()
    elif choice == "2":
        text = input("\nEnter your grocery order in any supported language: ")
        result = system.process_text_input(text)
    elif choice == "3":
        # List available audio files
        print("\nAvailable audio files in Sample Files:")
        try:
            files = [f for f in os.listdir(sample_files_dir) if f.lower().endswith(('.wav', '.flac', '.mp3', '.aiff', '.aifc'))]
        except Exception as e:
            print(f"Error accessing Sample Files folder: {e}")
            return
        if not files:
            print("No audio files found in Sample Files folder.")
            return
        for idx, fname in enumerate(files, 1):
            print(f"{idx}. {fname}")
        file_choice = input("Enter the number of the audio file to process: ").strip()
        try:
            file_idx = int(file_choice) - 1
            if file_idx < 0 or file_idx >= len(files):
                print("Invalid file selection.")
                return
            file_path = os.path.join(sample_files_dir, files[file_idx])
        except Exception:
            print("Invalid input.")
            return
        result = system.process_audio_file(file_path)
    else:
        print("Invalid choice")
        return
    
    if result:
        # Format and display the order
        formatted_order = system.format_order_list(result)
        
        print(f"\n--- ORDER PROCESSED ---")
        print(f"Language Detected: {formatted_order['language_detected'].title()}")
        print(f"Order ID: {formatted_order['order_id']}")
        print(f"Raw Input: {formatted_order['raw_input']}")
        print(f"Confidence: {formatted_order['confidence']:.2f}")
        print(f"\n--- GROCERY ITEMS ---")
        
        if formatted_order['items']:
            for i, item in enumerate(formatted_order['items'], 1):
                print(f"{i}. {item['name']} - {item['quantity']} {item['unit']} (confidence: {item['confidence']:.2f})")
        else:
            print("No grocery items detected")
        
        # Save order
        filepath = system.save_order(formatted_order)
        print(f"\nOrder saved to: {filepath}")
        
    else:
        print("Failed to process order")

if __name__ == "__main__":
    main() 