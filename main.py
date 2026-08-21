import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

# Render panelinden çekilecek şifreler
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GEMINI_API_KEY:
        return {"reply": "Hata: GEMINI_API_KEY Render panelinde tanımlı değil!"}

    # Gemini API Direkt REST Bağlantısı (En stabil yöntem)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
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

            # Yanıtı Ayıkla
            ai_reply = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"reply": ai_reply}

        except Exception as e:
            return {"reply": f"Sunucu Baglanti Hatasi: {str(e)}"}

@app.get("/")
async def read_index():
    return FileResponse("index.html")
