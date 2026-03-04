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
    # CONVERSATIONAL CORRECTION PIPELINE
    # =========================================================================

    # Correction trigger words (Tamil spoken/formal + English)
    CORRECTION_TRIGGERS = [
        r'\billa\b', r'\billai\b', r'\billama\b',
        r'இல்ல(?!\w)', r'இல்லை',           # Tamil-script "illa"/"illai"
        r'\balla\b',
        r'வேண்டாம்', r'வேண்டா', r'\bvendaam\b', r'\bvendama\b',
        r'\bno wait\b', r'\bwait\b', r'\bactually\b', r'\bnot that\b',
    ]

    def _detect_and_apply_correction(self, text: str):
        """
        Detects conversational corrections like:
          "oru kilo thakkali illa 2 kg venum"
          before: "oru kilo thakkali"  => item Tomato 1 kg
          after:  "2 kg venum"         => qty=2, unit=kg
          result: a corrected item dict: Tomato 2 kg

        Returns (corrected_item_dict_or_None, was_corrected: bool).
        - If correction detected: returns (corrected_item_dict, True)
        - Otherwise: returns (None, False)
        """
        combined_pattern = '|'.join(self.CORRECTION_TRIGGERS)
        parts = re.split(combined_pattern, text, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) < 2:
            return None, False   # No correction word found

        before = parts[0].strip().rstrip(',').strip()
        after  = parts[1].strip().lstrip(',').strip()

        logger.info(f"[Correction] before='{before}' | after='{after}'")

        # --- Extract the item from the BEFORE part ---
        before_items = self.processors['tamil']['veg'].extract_grocery_items(before)
        if not before_items:
            before_items = self.processors['tamil']['nonveg'].extract_grocery_items(before)

        if not before_items:
            logger.info("[Correction] No item found in before-part; skipping correction.")
            return None, False

        base_item = before_items[-1]   # LAST item before trigger = most recently mentioned

        # --- Check if after-part already has an item name ---
        # If it does, this is a different item being ordered, not a correction
        after_items = self.processors['tamil']['veg'].extract_grocery_items(after)
        if not after_items:
            after_items = self.processors['tamil']['nonveg'].extract_grocery_items(after)

        if after_items:
            logger.info("[Correction] After-part has its own item; treating as multi-item, not a correction.")
            return None, False

        # --- Extract only qty/unit from the after-part ---
        unit_map = {
            "kg": "kg", "kilogram": "kg", "kilo": "kg",
            "gram": "g", "g": "g", "gm": "g",
            "liter": "liter", "litre": "liter", "l": "liter",
            "ml": "ml",
            "packet": "packets", "packets": "packets", "pkt": "packets",
            "piece": "pieces", "pieces": "pieces", "pcs": "pieces",
            "bunch": "bunch", "bunches": "bunch",
            "tray": "tray", "\u0b9f\u0bcd\u0bb0\u0bc7": "tray", "dozen": "dozen",
            "\u0b95\u0bbf\u0bb2\u0bcb": "kg", "\u0b95\u0bbf\u0bb0\u0bbe\u0bae\u0bcd": "g",
        }
        qty_pattern = (
            r'(\d+(?:\.\d+)?)\s*'
            r'(kg|kilogram|kilo|gram|g|gm|liter|litre|l|ml|'
            r'packet|packets|pkt|piece|pieces|pcs|bunch|bunches|tray|dozen|'
            r'\u0b95\u0bbf\u0bb2\u0bcb|\u0b95\u0bbf\u0bb0\u0bbe\u0bae\u0bcd|\u0b9f\u0bcd\u0bb0\u0bc7)'
        )
        # Normalize numbers (Tamil word numbers -> digits)
        after_norm = self.processors['tamil']['veg'].normalize_numbers(
            self.processors['tamil']['nonveg'].normalize_numbers(after)
        )
        m = re.search(qty_pattern, after_norm, re.IGNORECASE)

        if not m:
            logger.info("[Correction] No qty/unit found in after-part; skipping correction.")
            return None, False

        new_qty  = m.group(1)
        new_unit = unit_map.get(m.group(2).lower(), m.group(2).lower())

        # --- Build the corrected item dict ---
        corrected_item = dict(base_item)   # copy the base item (keeps name, category, instructions)
        corrected_item['quantity'] = new_qty
        corrected_item['unit']     = new_unit
        corrected_item['confidence'] = 0.9   # high confidence for explicit correction

        logger.info(
            "[Correction] Applied: %s %s %s => %s %s %s",
            base_item['name'], base_item['quantity'], base_item['unit'],
            corrected_item['name'], corrected_item['quantity'], corrected_item['unit']
        )
        return corrected_item, True

    # =========================================================================
    # STATEFUL CART ENGINE  (multi-step corrections in one utterance)
    # =========================================================================

    # Signals that start the "correction block" in a complex utterance
    TRANSITION_MARKERS = [
        '\u2026',    # ellipsis character …
        r'\.\.\.',  # three dots
    ]

    # Signals used inside the correction block (Tamil script + romanized)
    CANCEL_SIGNAL    = r'வேண்டாம்|வேண்டா|\bvendaam\b|\bvendama\b'
    REPLACE_SIGNAL   = r'அதற்கு\s*பதிலா|பதிலா|\batharku\s*pathila\b|\binstead\b|\bpathila\b'
    UPDATE_SIGNALS   = r'மட்டும்\s*போதும்|போதும்|ஆக்குங்க|மட்டும்|\baakkuinga\b|\baakkunga\b|\bonly\b|\bpothum\b|\benough\b'

    def _is_complex_order(self, text: str) -> bool:
        """Returns True if the text contains multi-step correction markers."""
        for marker in self.TRANSITION_MARKERS:
            if re.search(marker, text):
                return True
        if re.search(self.REPLACE_SIGNAL, text):
            return True
        # A cancel signal (வேண்டாம் / vendaam) always means multi-step conversational order
        if re.search(self.CANCEL_SIGNAL, text, re.IGNORECASE):
            return True
        # Multiple item names + update signals = complex
        if re.search(self.UPDATE_SIGNALS, text):
            all_items = (self.processors['tamil']['veg'].extract_grocery_items(text) +
                         self.processors['tamil']['nonveg'].extract_grocery_items(text))
            if len(set(i['name'] for i in all_items)) >= 2:
                return True
        return False

    def _extract_qty_from_segment(self, segment: str):
        """Extract (qty, unit) from a text segment. Returns ('1', '') if nothing found."""
        unit_map = {
            'kg': 'kg', 'kilogram': 'kg', 'kilo': 'kg', '\u0b95\u0bbf\u0bb2\u0bcb': 'kg',
            'gram': 'g', 'g': 'g', 'gm': 'g', '\u0b95\u0bbf\u0bb0\u0bbe\u0bae\u0bcd': 'g',
            'liter': 'liter', 'litre': 'liter', 'l': 'liter',
            'ml': 'ml',
            'packet': 'packets', 'packets': 'packets', 'pkt': 'packets',
            'piece': 'pieces', 'pieces': 'pieces', 'pcs': 'pieces',
            '\u0baa\u0bc0ஸ்': 'pieces',  # பீஸ் Tamil for pieces
            'bunch': 'bunch', 'bunches': 'bunch',
            'tray': 'tray', '\u0b9f\u0bcd\u0bb0\u0bc7': 'tray',
            'dozen': 'dozen',
        }
        qty_re = (
            r'(\d+(?:\.\d+)?)\s*'
            r'(kg|kilogram|kilo|gram|g|gm|liter|litre|l|ml|'
            r'packet|packets|pkt|piece|pieces|pcs|bunch|bunches|tray|dozen|'
            r'\u0b95\u0bbf\u0bb2\u0bcb|\u0b95\u0bbf\u0bb0\u0bbe\u0bae\u0bcd|\u0b9f\u0bcd\u0bb0\u0bc7|\u0baa\u0bc0\u0bb8\u0bcd)'
        )
        norm = self.processors['tamil']['veg'].normalize_numbers(
            self.processors['tamil']['nonveg'].normalize_numbers(segment)
        )
        m = re.search(qty_re, norm, re.IGNORECASE)
        if m:
            return m.group(1), unit_map.get(m.group(2).lower(), m.group(2).lower())
        return '1', ''

    def _find_item_in_segment(self, segment: str) -> Optional[dict]:
        """Run both processors on a segment; return first item dict found, or None."""
        items = self.processors['tamil']['veg'].extract_grocery_items(segment)
        if not items:
            items = self.processors['tamil']['nonveg'].extract_grocery_items(segment)
        return items[0] if items else None

    def _process_complex_order(self, text: str) -> 'OrderResult':
        """
        Stateful cart engine for multi-step corrections in one utterance.

        Steps:
          1. Split at transition marker (… or similar) into initial + correction block.
          2. Extract initial cart from the initial block.
          3. Parse each correction segment:
             - Cancel:  [item] வேண்டாம்      → remove from cart
             - Replace: அதற்கு பதிலா [item]  → add new item
             - Update:  [item] [qty] மட்டும் → update qty/unit of existing item
          4. Return finalised cart as OrderResult.
        """
        is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
        detected_lang = 'tamil' if is_tamil else 'english'

        # ── 1. Split at the transition marker ──────────────────────────────
        transition_re = r'\u2026|\.\.\.(?=\s)'
        parts = re.split(transition_re, text, maxsplit=1)

        if len(parts) == 2:
            initial_block, correction_block = parts[0].strip(), parts[1].strip()
        else:
            # No ellipsis: scan comma-segments to find the first one with a cancel/replace signal
            all_segs = [s.strip() for s in re.split(r'[,;]', text) if s.strip()]
            split_at = None
            for idx, seg in enumerate(all_segs):
                if re.search(self.CANCEL_SIGNAL + '|' + self.REPLACE_SIGNAL, seg, re.IGNORECASE):
                    split_at = idx
                    break
            if split_at is not None and split_at > 0:
                initial_block    = ', '.join(all_segs[:split_at]).strip()
                correction_block = ', '.join(all_segs[split_at:]).strip()
            elif split_at == 0:
                # Correction starts right away — all is correction, no initial
                initial_block, correction_block = '', ', '.join(all_segs)
            else:
                initial_block, correction_block = text, ''

        logger.info('[Complex] initial="%s"', initial_block[:80])
        logger.info('[Complex] corrections="%s"', correction_block[:120])

        # ── 2. Build initial cart (segment-by-segment to prevent instruction bleed) ──
        # Split initial block on commas and extract items from each segment independently.
        # This ensures instructions like 'cleaned' for Fish don't spill into Mutton via
        # the proximity window when they're in the same sentence.
        initial_segs = [s.strip() for s in re.split(r'[,;]', initial_block) if s.strip()]
        raw_cart: list = []
        for seg in initial_segs:
            seg_items = (self.processors['tamil']['veg'].extract_grocery_items(seg) +
                         self.processors['tamil']['nonveg'].extract_grocery_items(seg))
            # Supplement instructions: the proximity window sometimes misses trailing
            # instructions (e.g. "பிரியாணி கட்" after item name). Re-run extract_instructions
            # on the full segment and merge any that were missed.
            full_seg_instrs = self.processors['tamil']['nonveg'].extract_instructions(seg)
            for item in seg_items:
                if full_seg_instrs and not item.get('instructions'):
                    item['instructions'] = full_seg_instrs
            raw_cart.extend(seg_items)

        # Deduplicate by name (keep first occurrence)
        seen, cart = set(), []
        for item in raw_cart:
            if item['name'] not in seen:
                seen.add(item['name'])
                cart.append(dict(item))

        logger.info('[Complex] Initial cart: %s', [i['name'] for i in cart])

        # ── 3. Parse correction segments ────────────────────────────────────
        if correction_block:
            # Split on , or ; — but NOT on . between digits (preserves decimals like 1.5)
            segs = [s.strip() for s in re.split(r'[,\uff0c;]|(?<!\d)\.(?!\d)', correction_block) if s.strip()]

            i = 0

            while i < len(segs):
                seg = segs[i]
                seg_lower = seg  # Tamil text — don't lower() it (it's already unicode)

                # ── A. REPLACE signal: அதற்கு பதிலா ──────────────────────
                if re.search(self.REPLACE_SIGNAL, seg):
                    # The new item is described in this segment (after the signal)
                    after_replace = re.split(self.REPLACE_SIGNAL, seg, maxsplit=1)[-1].strip()
                    new_item = self._find_item_in_segment(after_replace)
                    if new_item:
                        qty, unit = self._extract_qty_from_segment(after_replace)
                        new_item = dict(new_item)
                        new_item['quantity'] = qty
                        new_item['unit']     = unit if unit else new_item.get('unit', 'kg')
                        # Also grab instructions (e.g. biryani cut)
                        new_item['instructions'] = (
                            self.processors['tamil']['nonveg'].extract_instructions(after_replace)
                        )
                        # Remove duplicate if same name already in cart
                        cart = [c for c in cart if c['name'] != new_item['name']]
                        cart.append(new_item)
                        logger.info('[Complex] Replace => added %s %s %s instr=%s',
                                    new_item['name'], new_item['quantity'],
                                    new_item['unit'], new_item['instructions'])
                    i += 1
                    continue

                # ── B. CANCEL signal: [item] வேண்டாம் ────────────────────
                if re.search(self.CANCEL_SIGNAL, seg):
                    # Find which item is being cancelled
                    before_cancel = re.split(self.CANCEL_SIGNAL, seg)[0].strip()
                    target = self._find_item_in_segment(before_cancel)
                    if target:
                        before_len = len(cart)
                        cart = [c for c in cart if c['name'] != target['name']]
                        logger.info('[Complex] Cancel %s (removed %d)',
                                    target['name'], before_len - len(cart))
                    i += 1
                    continue

                # ── C. UPDATE signal: [item] [qty] மட்டும்/ஆக்குங்க ─────
                if re.search(self.UPDATE_SIGNALS, seg):
                    target = self._find_item_in_segment(seg)
                    if target:
                        qty, unit = self._extract_qty_from_segment(seg)
                        new_instrs = self.processors['tamil']['nonveg'].extract_instructions(seg)
                        for c in cart:
                            if c['name'] == target['name']:
                                old_qty, old_unit = c['quantity'], c['unit']
                                c['quantity'] = qty
                                if unit:
                                    c['unit'] = unit
                                if new_instrs:  # update instructions if any found
                                    c['instructions'] = new_instrs
                                logger.info('[Complex] Update %s: %s %s => %s %s instr=%s',
                                            c['name'], old_qty, old_unit, qty, c['unit'], new_instrs)
                                break
                    i += 1
                    continue

                # ── D. IMPLICIT update/add: item + qty, no explicit signal ─
                # If segment has an item + qty but none of A/B/C signals matched:
                #   - item already in cart → update qty/unit/instructions
                #   - item not in cart    → add as new item
                target = self._find_item_in_segment(seg)
                if target:
                    qty, unit = self._extract_qty_from_segment(seg)
                    new_instrs = self.processors['tamil']['nonveg'].extract_instructions(seg)
                    cart_names = [c['name'] for c in cart]
                    if target['name'] in cart_names:
                        for c in cart:
                            if c['name'] == target['name']:
                                c['quantity'] = qty
                                if unit:
                                    c['unit'] = unit
                                if new_instrs:
                                    c['instructions'] = new_instrs
                                logger.info('[Complex] Implicit-update %s => %s %s', target['name'], qty, unit)
                                break
                    else:
                        new_entry = dict(target)
                        new_entry['quantity'] = qty
                        new_entry['unit'] = unit if unit else target.get('unit', 'kg')
                        new_entry['instructions'] = new_instrs
                        cart.append(new_entry)
                        logger.info('[Complex] Implicit-add %s %s %s', target['name'], qty, unit)

                i += 1

        # ── 4. Build final OrderResult ──────────────────────────────────────
        final_items = []
        for raw in cart:
            name  = raw.get('name') or raw.get('local_name', '')
            qty   = str(raw.get('quantity', '1'))
            unit  = raw.get('unit', '')
            conf  = raw.get('confidence', 0.85)
            instr = raw.get('instructions', [])
            # Egg unit override
            if name == 'Egg' and unit == 'kg':
                unit = 'tray'
            final_items.append(GroceryItem(name=name, quantity=qty,
                                           unit=unit, confidence=conf,
                                           instructions=instr))

        avg_conf = (sum(i.confidence for i in final_items) / len(final_items)
                    if final_items else 0.0)
        logger.info('[Complex] Final cart: %s', [(i.name, i.quantity, i.unit)
                                                  for i in final_items])
        return OrderResult(items=final_items, language_detected=detected_lang,
                           raw_text=text, confidence=avg_conf)

    # =========================================================================
    # EXTRACTION PIPELINE (Regex Logic)
    # =========================================================================


    def process_text_input(self, text: str) -> OrderResult:
        if not text:
            return OrderResult([], "unknown", "", 0.0)

        original_text = text  # keep original for raw_text field

        # 0a. Complex multi-step order? Route to stateful cart engine FIRST
        if self._is_complex_order(text):
            logger.info('[Router] Complex order detected — using stateful cart engine.')
            return self._process_complex_order(text)

        # 0b. Simple single correction? (e.g. "oru kilo thakkali illa 2 kg venum")
        corrected_item, was_corrected = self._detect_and_apply_correction(text)

        if was_corrected:
            logger.info('[Correction Applied] %r => %r %r %r',
                        original_text, corrected_item['name'],
                        corrected_item['quantity'], corrected_item['unit'])
            is_tamil = bool(re.search(r'[\u0B80-\u0BFF]', text))
            detected_lang = 'tamil' if is_tamil else 'english'

            # Build the corrected GroceryItem
            corrected_gi = GroceryItem(
                name=corrected_item['name'],
                quantity=str(corrected_item['quantity']),
                unit=corrected_item['unit'],
                confidence=corrected_item.get('confidence', 0.9),
                instructions=corrected_item.get('instructions', [])
            )

            # Also keep any OTHER items from the before-part
            combined_pattern = '|'.join(self.CORRECTION_TRIGGERS)
            before_text = re.split(combined_pattern, text, maxsplit=1, flags=re.IGNORECASE)[0]
            before_text = before_text.strip().rstrip(',').strip()
            other_raw = (self.processors['tamil']['veg'].extract_grocery_items(before_text) +
                         self.processors['tamil']['nonveg'].extract_grocery_items(before_text))
            other_items = [
                GroceryItem(name=r['name'], quantity=str(r['quantity']),
                            unit=r['unit'], confidence=r.get('confidence', 0.85),
                            instructions=r.get('instructions', []))
                for r in other_raw
                if r['name'] != corrected_item['name']   # exclude the one we just corrected
            ]
            # Deduplicate other_items by name
            seen_names, deduped = set(), []
            for gi in other_items:
                if gi.name not in seen_names:
                    seen_names.add(gi.name)
                    deduped.append(gi)

            all_items = deduped + [corrected_gi]
            avg_conf = sum(i.confidence for i in all_items) / len(all_items)
            return OrderResult(items=all_items, language_detected=detected_lang,
                               raw_text=original_text, confidence=avg_conf)


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
            nonveg_instructions=[]
            for item in all_extracted_items:
                if isinstance(item,dict) and item.get("category")=="meat":
                    nonveg_instructions.extend(item.get("instructions",[]))
            nonveg_instructions=list(set(nonveg_instructions))
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
            raw_text=original_text,   # always return the original input, not the corrected version
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