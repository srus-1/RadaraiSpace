import os
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from dotenv import load_dotenv
from aiohttp import web
import asyncio

# Load file .env biar API key lu nggak bocor kalau di-push ke GitHub
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inisialisasi Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Gas ngab! Kirim aja poster event, beasiswa, atau lomba ke sini. "
        "Ntar gw ekstrak jadi teks rapi yang tinggal lu copy-paste buat di-broadcast."
    )
    await update.message.reply_text(welcome_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kasih feedback biar user tau bot nggak nge-hang
    processing_msg = await update.message.reply_text("⏳ Bentar, lagi nge-scan poster...")

    try:
        # Ambil gambar resolusi paling tinggi (index -1)
        photo_file = await update.message.photo[-1].get_file()
        
        # Download gambar langsung ke memory (RAM), nggak usah menuhin storage lokal
        out = BytesIO()
        await photo_file.download_to_memory(out)
        out.seek(0)
        image_bytes = out.read()

       # Prompt khusus buat copywriting broadcast WhatsApp/IG yang lebih panjang dan asik
        prompt = """
        Lu adalah asisten admin komunitas mahasiswa Gen Z yang asik, gaul, dan jago bikin orang FOMO. 
        Tugas lu membaca poster event/lomba/beasiswa dan membuat teks broadcast WhatsApp yang komprehensif.

        🔴 ATURAN MUTLAK: 
        1. HANYA gunakan informasi yang SECARA VISUAL TERLIHAT di dalam poster.
        2. JANGAN PERNAH mengarang, menebak, atau menambahkan informasi (tanggal, harga, syarat, link) yang tidak tertulis secara harfiah di gambar.
        3. Jika sebuah informasi (misalnya Harga atau Deadline) tidak ada di poster, tulis dengan jelas: "Tidak disebutkan di poster".

        Wajib gunakan struktur dan format markdown WhatsApp (* untuk tebal) di bawah ini:
        
        *[Judul Kegiatan / Beasiswa]* 🔥
        
        (Buat 1 kalimat pembuka yang asik dan bikin FOMO)
        
        📝 *Deskripsi Singkat:*
        (Jelaskan inti acaranya apa berdasarkan poster)
        
        🎯 *Syarat / Target Peserta:* 
        (Sebutkan siapa aja yang bisa ikut berdasarkan poster)
        
        💸 *HTM / Biaya Pendaftaran:*
        (Sebutkan harga tiket. Jika tidak ada, tulis "Tidak disebutkan di poster")

        🎁 *Benefit:* 
        (Sebutkan keuntungan sesuai poster)
        
        🗓 *Timeline / Deadline:* 
        (Tanggal penting sesuai poster)
        
        🔗 *Link Daftar:* 
        (Ekstrak URL/link dari poster. Jika tidak ada, arahkan untuk cek Instagram penyelenggara)
        """

        # Panggil API Gemini (Gemini 2.5 Flash cocok banget buat OCR cepat & murah)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                prompt
            ]
        )

        # Timpa pesan "loading" dengan hasil akhirnya
        await processing_msg.edit_text(response.text)
        
    except Exception as e:
        await processing_msg.edit_text(f"Waduh, ada error di back-end nih: {e}")

async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        print("Error: Token/API Key belum diset")
        return

    # Build bot application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Jalankan Web Server dan Bot berbarengan
    await web_server()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Biar nggak mati
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())