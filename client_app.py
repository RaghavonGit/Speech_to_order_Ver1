import requests
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile
import os

API_URL = "http://127.0.0.1:5000"

def record_audio(duration=7, fs=44100):
    print(f"Recording for {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("Recording complete.")
    
    fd, filename = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wav.write(filename, fs, recording)
    return filename

def send_request(endpoint, data=None, files=None):
    try:
        if files:
            response = requests.post(f"{API_URL}{endpoint}", files=files)
        else:
            response = requests.post(f"{API_URL}{endpoint}", json=data)
            
        if response.status_code == 200:
            print_response(response.json())
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

def print_response(data):
    print("\n" + "="*40)
    print("🛍️  ORDER PROCESSED")
    print("="*40)
    print(f"Language:   {data['language_detected']}")
    print(f"Original:   {data['raw_input']}")
    print(f"Translated: {data['translated_text']}")
    print("-" * 40)
    print("Items:")
    for item in data['items']:
        print(f" - {item['name']:<15} : {item['quantity']} {item['unit']}")
    print("="*40 + "\n")

def main():
    print("Connecting to Server...")
    try:
        requests.get(f"{API_URL}/health")
        print("✅ Server Online")
    except:
        print("❌ Server Offline. Run 'python app.py' first.")
        return

    while True:
        print("\n1. Text Input\n2. Live Voice\n3. Upload File\n4. Exit")
        choice = input("Choice: ")

        if choice == '1':
            text = input("Order: ")
            send_request("/order/text", data={"text": text})
        elif choice == '2':
            path = record_audio()
            with open(path, 'rb') as f:
                send_request("/order/audio", files={'file': f})
            os.remove(path)
        elif choice == '3':
            path = input("File Path: ").strip('"')
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    send_request("/order/audio", files={'file': f})
            else:
                print("File not found.")
        elif choice == '4':
            break

if __name__ == "__main__":
    main()