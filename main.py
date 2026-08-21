import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import genai
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

# CORS Ayarları (Web arayüzünün sorunsuz erişimi için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ortam Değişkenleri (Render paneline gireceğimiz gizli şifreler)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Gemini Client Yapılandırması
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# MongoDB Bağlantısı
mongo_client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
db = mongo_client["ai_app_db"] if mongo_client else None

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not ai_client:
        raise HTTPException(status_code=500, detail="Gemini API Anahtarı eksik!")

    try:
        # 1. Yapay Zekadan Yanıt Al
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=request.message,
        )
        ai_reply = response.text

        # 2. Verileri MongoDB Atlas'a Kaydet
        if db is not None:
            await db.chat_history.insert_one({
                "user_id": request.user_id,
                "user_message": request.message,
                "bot_response": ai_reply
            })

        return {"status": "success", "reply": ai_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ana Sayfa Erişimi
@app.get("/")
async def read_index():
    return FileResponse("index.html")
