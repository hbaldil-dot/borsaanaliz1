import os
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GEMINI_API_KEY:
        return {"reply": "Hata: GEMINI_API_KEY Render panelinde tanımlı değil!"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": request.message}]}]}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()

            if response.status_code != 200:
                error_msg = data.get("error", {}).get("message", "API hatası")
                return {"reply": f"Gemini API Hatası ({response.status_code}): {error_msg}"}

            ai_reply = data["candidates"][0]["content"]["parts"][0]["text"]

            db_status = ""
            if MONGO_URI:
                try:
                    mongo_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
                    db = mongo_client["borsaanaliz1_db"]
                    
                    await db["chat_history"].insert_one({
                        "user_id": request.user_id,
                        "user_message": request.message,
                        "bot_response": ai_reply
                    })
                    mongo_client.close()
                except Exception as db_err:
                    db_status = f"\n\n[Veritabanı Kayıt Hatası: {str(db_err)}]"
            else:
                db_status = "\n\n[Veritabanı Uyarısı: MONGO_URI bulunamadı]"

            return {"reply": ai_reply + db_status}

        except Exception as e:
            return {"reply": f"Sunucu Bağlantı Hatası: {str(e)}"}

@app.get("/")
async def read_index():
    return FileResponse("index.html")
