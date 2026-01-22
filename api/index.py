import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import google.generativeai as genai

# --------------------------------------------------
# Load environment
# --------------------------------------------------
load_dotenv()
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --------------------------------------------------
# Configure Gemini
# --------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# --------------------------------------------------
# FastAPI setup
# --------------------------------------------------
app = FastAPI()

# Add session middleware immediately after app creation
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR = Path(__file__).parent
PRODUCTS_PATH = BASE_DIR / "products.json"
ARTICLE_PATH = BASE_DIR / "article.txt"

# --------------------------------------------------
# Load products.json
# --------------------------------------------------
try:
    with PRODUCTS_PATH.open("r", encoding="utf-8") as f:
        PRODUCT_DATA = json.load(f)
except Exception as e:
    print("❌ Failed to load products.json:", e)
    PRODUCT_DATA = {"brands": []}

print("✅ Brands loaded:", len(PRODUCT_DATA.get("brands", [])))

# --------------------------------------------------
# Load article.txt
# --------------------------------------------------
try:
    ARTICLE_TEXT = ARTICLE_PATH.read_text(encoding="utf-8")
except Exception as e:
    print("❌ Failed to load article.txt:", e)
    ARTICLE_TEXT = ""

# --------------------------------------------------
# Utility functions
# --------------------------------------------------
def get_all_products():
    products = []
    for brand in PRODUCT_DATA.get("brands", []):
        brand_name = brand.get("brand_name", "Unknown Brand")
        for product in brand.get("products", []):
            p = product.copy()
            p["brand"] = brand_name
            products.append(p)
    return products

def format_products_for_prompt(products):
    formatted = ""
    for p in products:
        formatted += f"""
Product Name: {p.get('name', 'N/A')}
Brand: {p.get('brand', 'N/A')}
Category: {p.get('category', 'N/A')}
Features: {p.get('features', 'N/A')}
Usage Instructions: {p.get('usage_instructions', 'N/A')}
Ingredients: {', '.join(p.get('ingredients', []))}
Price: {p.get('price_bdt', 'N/A')} BDT
Suitability: {p.get('suitability', 'N/A')}
---
"""
    return formatted

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/")
async def home():
    return {"message": "Chatbot API is running!"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = (data.get("message") or "").strip()
    temperature = float(data.get("temperature", 0.4))

    if not user_message:
        return JSONResponse({"reply": "Please ask a question! 😊"})

    session = request.session
    if "chat_history" not in session:
        session["chat_history"] = []

    # Initialize system instruction once per session
    if "system_instruction" not in session:
        products_context = format_products_for_prompt(get_all_products())
        session["system_instruction"] = f"""
You are a professional customer service officer for Lira Cosmetics Ltd.

Company Info:
{ARTICLE_TEXT}

Products:
{products_context}

Rules:
- Answer ONLY based on this data.
- Be clear, polite, and customer-friendly.
- Do NOT invent information.
"""
    system_instruction = session["system_instruction"]

    try:
        chat_obj = model.start_chat(history=session["chat_history"])

        if not session.get("system_sent", False):
            chat_obj.send_message(
                system_instruction,
                generation_config={
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 512
                }
            )
            session["system_sent"] = True

        response = chat_obj.send_message(
            user_message,
            generation_config={
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 512
            }
        )
        reply = response.text.strip()

        # Save chat history
        new_history = []
        for msg in chat_obj.history:
            parts = [{"text": part.text} for part in msg.parts]
            new_history.append({"role": msg.role, "parts": parts})
        session["chat_history"] = new_history

    except Exception as e:
        print("❌ Gemini error:", e)
        reply = "I'm having trouble answering right now. Please try again."

    return JSONResponse({"reply": reply})

