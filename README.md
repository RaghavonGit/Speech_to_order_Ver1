# Speech-to-Order Ver 1.2

A voice-driven grocery ordering system for South Indian languages (Tamil/Telugu). Converts spoken grocery orders — including conversational corrections — into structured item lists with quantities and units.

---

## Features

- **Voice & Text input** — accepts audio files or raw text
- **Tamil & Telugu support** — handles Tamil script, romanized Tamil, and English
- **Conversational corrections** — understands multi-step spoken corrections in a single utterance:
  - Cancel: `சிக்கன் வேண்டாம்` (don't want chicken)
  - Replace: `அதற்கு பதிலா மட்டன்` (instead of that, mutton)
  - Update quantity: `தக்காளி 1.5 கிலோ மட்டும்` (just 1.5 kg tomato)
- **Comma-free voice segmentation** — handles natural speech with no punctuation
- **Compound fraction support** — `ஒன்னேகால்` → 1.25, `ரெண்டரை` → 2.5, `1/2` → 0.5
- **Spoken unit variants** — `கிலோ`, `கிராம்`, `டிரே`, `டே` etc.
- **Translation** — translates Tamil/Telugu input to English using AI4Bharat IndicTrans2
- **REST API** — Flask server with web UI and client API endpoints
- **Order persistence** — saves each order as a JSON file

---

## Project Structure

```
├── app.py                 # Flask API + web interface
├── grocery_system.py      # Core engine: STT, correction pipeline, cart logic
├── veg_processor.py       # Vegetable/pantry item extraction
├── nonveg_processor.py    # Meat item extraction + cooking instructions
├── tamil_processor.py     # Legacy Tamil helpers
├── telugu_processor.py    # Legacy Telugu helpers
├── base_processor.py      # Abstract base class
├── config.py              # Configuration
├── test_correction.py     # Correction pipeline tests
└── orders/                # Saved order JSON files (auto-created)
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web interface |
| `POST` | `/process_text` | Process text input |
| `POST` | `/process_audio` | Process audio file upload |
| `GET` | `/health` | Health check |
| `POST` | `/order/text` | Client API — text order |
| `POST` | `/order/audio` | Client API — audio order |

### Example Request

```bash
curl -X POST http://localhost:5000/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "ரெண்டு கிலோ தக்காளி ஒரு கிலோ வெங்காயம்"}'
```

### Example Response

```json
{
  "order_id": "ORDER_1234567890",
  "language_detected": "tamil",
  "items": [
    { "name": "Tomato", "quantity": "2", "unit": "kg", "instructions": [] },
    { "name": "Onion",  "quantity": "1", "unit": "kg", "instructions": [] }
  ],
  "confidence": 0.875
}
```

---

## Setup

### Requirements

- Python 3.8+
- FFmpeg (for audio conversion)

### Install Dependencies

```bash
pip install flask torch transformers speechrecognition pydub
```

### Run

```bash
python app.py
```

Server starts at `http://0.0.0.0:5000`.

> **Windows note:** Tamil Unicode in the terminal requires `PYTHONIOENCODING=utf-8`.

---

## Translation Model

Uses [AI4Bharat IndicTrans2](https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M) (`indictrans2-indic-en-dist-200M`) for Tamil/Telugu → English translation. Downloaded automatically on first run. Falls back to raw text if the model is unavailable.

---

## Supported Languages

| Language | Script | Romanized | STT Code |
|----------|--------|-----------|----------|
| Tamil | ✅ | ✅ | `ta-IN` |
| Telugu | ✅ | — | `te-IN` |
| English | — | ✅ | `en-IN` (fallback) |

---

## Running Tests

```bash
python test_correction.py
```
