from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv
import json
import os
import re
import requests
from pathlib import Path

# --------------------------------------------------
# Setup
# --------------------------------------------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_FILE_DIR=os.path.join(os.getcwd(), "flask_sessions"),
    SESSION_FILE_THRESHOLD=500
)

Session(app)

# --------------------------------------------------
# Hugging Face Setup
# --------------------------------------------------


HF_API_URL = "https://api-inference.huggingface.co/rafi25003/lira-cosmetics-qwen-1.5b"
HF_HEADERS = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
MAX_PROMPT_CHARS = 3000  # Prevent payload overflow on HF free tier


def query_huggingface(prompt):
    # Trim prompt if too large
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[-MAX_PROMPT_CHARS:]
        print(f"⚠️ Prompt trimmed to {MAX_PROMPT_CHARS} chars")

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
            "return_full_text": False,  # Only return newly generated tokens
            "do_sample": True,
        }
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json=payload,
            timeout=60  # Allow time for cold-start
        )

        print(f"HF Status: {response.status_code}")
        print(f"HF Body preview: {response.text[:300]!r}")

        # Model still loading
        if response.status_code == 503:
            return [{"generated_text": "Model is loading, please wait a moment and try again."}]

        # Any other HTTP error
        if not response.ok:
            print(f"❌ HF HTTP error: {response.status_code} - {response.text}")
            return [{"generated_text": "Error connecting to AI model."}]

        # Empty body guard
        if not response.text.strip():
            print("❌ HF returned empty body")
            return [{"generated_text": "Error connecting to AI model."}]

        result = response.json()

        # HF model-level error (e.g. token limit, bad input)
        if isinstance(result, dict) and "error" in result:
            print(f"❌ HF model error: {result['error']}")
            if "loading" in result["error"].lower():
                return [{"generated_text": "Model is loading, please try again in a moment."}]
            return [{"generated_text": "Error connecting to AI model."}]

        return result

    except requests.exceptions.Timeout:
        print("❌ HF request timed out")
        return [{"generated_text": "The AI model took too long to respond. Please try again."}]
    except Exception as e:
        print(f"❌ HF request error: {e}")
        return [{"generated_text": "Error connecting to AI model."}]


# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_PATH = os.path.join(BASE_DIR, "products.json")
ARTICLE_PATH = os.path.join(BASE_DIR, "article.txt")

# --------------------------------------------------
# Load product data
# --------------------------------------------------
try:
    with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
        PRODUCT_DATA = json.load(f)
except Exception as e:
    print("❌ Failed to load products.json:", e)
    PRODUCT_DATA = {"brands": []}

# --------------------------------------------------
# Load company article
# --------------------------------------------------
try:
    with open(ARTICLE_PATH, "r", encoding="utf-8") as f:
        ARTICLE_TEXT = f.read()
except Exception as e:
    print("❌ Failed to load article.txt:", e)
    ARTICLE_TEXT = ""

# --------------------------------------------------
# Build system instruction once at startup (not per session)
# --------------------------------------------------
SYSTEM_INSTRUCTION = f"""You are a professional customer service officer for Lira Cosmetics Ltd.

Company Info:
{ARTICLE_TEXT}

Products:
{chr(10).join(
    f"Product Name: {p.get('name')} | Brand: {p.get('brand_name', 'Unknown')} | "
    f"Category: {p.get('category')} | Price: {p.get('price_bdt')} BDT | "
    f"Suitability: {p.get('suitability')}"
    for brand in PRODUCT_DATA.get("brands", [])
    for p in brand.get("products", [])
)}

Rules:
- Answer ONLY using the company and product data above.
- Keep replies short (2-3 sentences).
- No emojis, no bullet points.
- If asked in Bangla, reply in polite natural Bangla. Otherwise reply in polite natural English.
"""


# --------------------------------------------------
# Utilities
# --------------------------------------------------
def detect_language(text):
    return "bn" if re.search(r"[\u0980-\u09FF]", text) else "en"


def build_prompt(chat_history, user_message):
    """Convert message list into a plain-text prompt for HF text-gen models."""
    prompt = SYSTEM_INSTRUCTION + "\n"

    for msg in chat_history:
        if msg["role"] == "user":
            prompt += f"User: {msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n"

    prompt += f"User: {user_message}\nAssistant:"
    return prompt


def extract_reply(output):
    """Safely extract the assistant reply from HF output."""
    try:
        text = output[0].get("generated_text", "").strip()
        if not text:
            return None
        # If model echoed the prompt back (return_full_text=True fallback), split it
        if "Assistant:" in text:
            text = text.split("Assistant:")[-1].strip()
        return text or None
    except (IndexError, KeyError, TypeError):
        return None


# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please ask a question.", "lang": "en"})

    lang = detect_language(user_message)

    if "chat_history" not in session:
        session["chat_history"] = []

    try:
        prompt = build_prompt(session["chat_history"], user_message)
        output = query_huggingface(prompt)

        print("HF RAW OUTPUT:", output)

        reply = extract_reply(output)

        if not reply:
            reply = (
                "দুঃখিত, এই মুহূর্তে উত্তর দিতে পারছি না।"
                if lang == "bn"
                else "Sorry, I couldn't generate a proper response."
            )

        # Keep only last 6 messages (3 turns) to limit session size
        session["chat_history"] = (
            session["chat_history"] + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply}
            ]
        )[-6:]
        session.modified = True

    except Exception as e:
        print(f"❌ Chat error: {e}")
        reply = (
            "এই মুহূর্তে উত্তর দিতে সমস্যা হচ্ছে।"
            if lang == "bn"
            else "I'm having trouble answering right now."
        )

    return jsonify({"reply": reply, "lang": lang})


@app.route("/reset", methods=["POST"])
def reset():
    """Clear chat history for the current session."""
    session.pop("chat_history", None)
    return jsonify({"status": "ok", "message": "Chat history cleared."})


# --------------------------------------------------
# TTS (disabled)
# --------------------------------------------------
TTS_DIR = Path("static/tts")
TTS_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/tts", methods=["POST"])
def tts():
    return jsonify({"error": "TTS disabled for now"}), 500


# --------------------------------------------------
# Run
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)