import os
import requests
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Token Telegram atau API Key Gemini belum di-set di file .env!")


client = genai.Client(api_key=GEMINI_API_KEY)
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

@app.route('/api/index', methods=['POST'])
def webhook():

    update = request.get_json()
    
    if "message" in update and "photo" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        
        send_message(chat_id, "⏳ Bentar, lagi nge-scan poster...")
        
        try:
            photo = update["message"]["photo"][-1]
            file_id = photo["file_id"]
            
            file_resp = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}").json()
            file_path = file_resp["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            
            image_resp = requests.get(file_url)
            image_bytes = image_resp.content

            prompt = """
            Lu adalah asisten admin komunitas mahasiswa Gen Z yang asik, gaul, dan jago bikin orang FOMO. 
            Tugas lu membaca poster event/lomba/beasiswa dan membuat teks broadcast WhatsApp yang komprehensif.

            🔴 ATURAN MUTLAK: 
            1. HANYA gunakan informasi yang SECARA VISUAL TERLIHAT di dalam poster.
            2. JANGAN PERNAH mengarang, menebak, atau menambahkan informasi yang tidak tertulis secara harfiah.
            3. Jika sebuah informasi (misal Harga/Deadline) tidak ada, tulis: "Tidak disebutkan di poster".
            
            Wajib gunakan format markdown WhatsApp (* untuk tebal) di bawah ini:
            *[Judul Kegiatan / Beasiswa]* 🔥
            (1 kalimat pembuka asik bikin FOMO)
            
            📝 *Deskripsi Singkat:*
            (Inti acara)
            🎯 *Syarat / Target Peserta:* 
            (Siapa aja yang bisa ikut)
            💸 *HTM / Biaya Pendaftaran:*
            (Harga tiket/Gratis)
            🎁 *Benefit:* 
            (Keuntungan)
            🗓 *Timeline / Deadline:* 
            (Tanggal penting)
            🔗 *Link Daftar:* 
            (Link di poster, atau arahkan cek IG penyelenggara)
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                    prompt
                ]
            )

            send_message(chat_id, response.text)
            
        except Exception as e:
            send_message(chat_id, f"Waduh, ada error di back-end nih: {e}")

    elif "message" in update and "text" in update["message"]:
        if update["message"]["text"] == "/start":
            chat_id = update["message"]["chat"]["id"]
            send_message(chat_id, "Gas ngab! Kirim aja poster event ke sini...")
            

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(debug=True)