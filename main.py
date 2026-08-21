import os
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Bağlantısı
mongo_client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
db = mongo_client["ai_app_db"] if mongo_client else None

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GEMINI_API_KEY:
        return {"reply": "Hata: GEMINI_API_KEY Render panelinde tanımlı değil!"}

    # Güncel Gemini 3.6 REST API Endpoint Adresi
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": request.message}]
        }]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()

            if response.status_code != 200:
                error_msg = data.get("error", {}).get("message", "Bilinmeyen API hatası")
                return {"reply": f"Gemini API Hatası ({response.status_code}): {error_msg}"}

            ai_reply = data["candidates"][0]["content"]["parts"][0]["text"]

            # Mesajı MongoDB Atlas'a Kaydetme
            if db is not None:
                try:
                    await db.chat_history.insert_one({
                        "user_id": request.user_id,
                        "user_message": request.message,
                        "bot_response": ai_reply
                    })
                except Exception as db_err:
                    print(f"MongoDB Kayıt Hatası: {db_err}")

            return {"reply": ai_reply}

        except Exception as e:
            return {"reply": f"Sunucu Baglanti Hatasi: {str(e)}"}

@app.get("/")
async def read_index():
    return FileResponse("index.html")
