#!/usr/bin/env python3
"""
Flask API for South Indian Grocery Order System
"""

import os
import time
from flask import Flask, request, jsonify, render_template, url_for
from werkzeug.utils import secure_filename
from grocery_system import SpeechToTextGrocerySystem

app = Flask(__name__, static_folder='static')

# Initialize the System Engine
print("Initializing Engine... Please wait.")
system = SpeechToTextGrocerySystem()
print("Engine Ready!")

# Configuration
AUDIO_FOLDER = os.path.join('static', 'audio')
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# -----------------------------------------------------------------------------
# WEB INTERFACE ROUTES
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    try:
        data = request.json
        text = data.get('text', '')
        
        # 1. Process Text
        result = system.process_text_input(text)
        
        # 2. Format & Translate
        formatted = system.format_order_list(result)
        
        # 3. Save
        system.save_order(formatted)
        
        return jsonify(formatted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio data received'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save file safely
    filename = secure_filename(audio_file.filename) or "recording.wav"
    timestamp = int(time.time())
    unique_filename = f"web_{timestamp}_{filename}"
    save_path = os.path.join(AUDIO_FOLDER, unique_filename)
    audio_file.save(save_path)

    try:
        # 1. Process Audio
        result = system.process_audio_file(save_path)
        
        if result:
            # 2. Format & Translate
            formatted = system.format_order_list(result)
            print(f"DEBUG:Audio Text:{result.raw_text}")
            print(f"DEBUG:Items Found:{len(result.items)}")
                
            
            # 3. Save
            system.save_order(formatted)
            
            # 4. Return with audio URL for playback
            formatted['audio_url'] = url_for('static', filename=f'audio/{unique_filename}')
            return jsonify(formatted)
        else:
            return jsonify({'error': 'Could not recognize speech or audio is empty'}), 422
            
    except Exception as e:
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

# -----------------------------------------------------------------------------
# CLIENT API ROUTES (For client_app.py)
# -----------------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "device": system.device})

@app.route('/order/text', methods=['POST'])
def order_by_text_api():
    return process_text()

@app.route('/order/audio', methods=['POST'])
def order_by_audio_api():
    # Map 'file' (from client script) to 'audio' (expected by web logic)
    if 'file' in request.files:
        request.files['audio'] = request.files['file']
    return process_audio()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)