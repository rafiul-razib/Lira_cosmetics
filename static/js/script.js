// ------------------------------------
// Timing constants
// ------------------------------------
const BOT_REPLY_DELAY = 1200;
const LISTEN_RESTART_DELAY = 700;
const USER_SILENCE_TIMEOUT = 7000;

// ------------------------------------
// Global state
// ------------------------------------
let recognition;
let isConversationActive = false;
let isBotSpeaking = false;
let recognitionReady = true;
let silenceTimer = null;
let availableVoices = [];

// ------------------------------------
// Load voices properly
// ------------------------------------
function loadVoices() {
  availableVoices = window.speechSynthesis.getVoices();
}

window.speechSynthesis.onvoiceschanged = loadVoices;
loadVoices(); // initial attempt

// ------------------------------------
// Speech Recognition Setup
// ------------------------------------
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

const micBtn = document.getElementById("micBtn");
const userInput = document.getElementById("user-input");

if (!SpeechRecognition) {
  micBtn.disabled = true;
  micBtn.innerText = "🎤 Not supported";
} else {
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    recognitionReady = false;
     micBtn.classList.add("pulsing"); // Start pulsing
    startSilenceTimer();
  };

  recognition.onend = () => {
    recognitionReady = true;
     micBtn.classList.remove("pulsing"); // Start pulsing
    clearTimeout(silenceTimer);
  };

  recognition.onresult = (event) => {
    if (!isConversationActive || isBotSpeaking) return;

    clearTimeout(silenceTimer);

    const transcript = event.results[0][0].transcript.trim();
    if (!transcript) return;

    recognition.stop();
    userInput.value = transcript;
    sendMessage();
  };

  recognition.onerror = () => {
    recognition.stop();
  };
}

// ------------------------------------
// Mic button toggle
// ------------------------------------
micBtn.onclick = () => {
  isConversationActive = !isConversationActive;

  if (isConversationActive) {
    micBtn.innerText = "🎙...";
     micBtn.classList.add("pulsing"); // Start pulsing
    safeStartRecognition();
  } else {
    micBtn.innerText = "🛑";
     micBtn.classList.remove("pulsing"); // Start pulsing
    recognition.stop();
    window.speechSynthesis.cancel();
    clearTimeout(silenceTimer);
  }
};

// ------------------------------------
// Safe recognition starter
// ------------------------------------
function safeStartRecognition() {
  if (!isConversationActive || isBotSpeaking) return;

  setTimeout(() => {
    if (recognitionReady) {
      try {
        recognition.start();
         micBtn.classList.add("pulsing"); // Start pulsing
      } catch {
        setTimeout(safeStartRecognition, 500);
      }
    }
  }, 300);
}

// ------------------------------------
// Silence timer
// ------------------------------------
function startSilenceTimer() {
  clearTimeout(silenceTimer);
  silenceTimer = setTimeout(() => {
    if (isConversationActive && !isBotSpeaking) {
      recognition.stop();
    }
  }, USER_SILENCE_TIMEOUT);
}

// ------------------------------------
// Send message to AI
// ------------------------------------
async function sendMessage() {
  const message = userInput.value.trim();
  if (!message) return;

  addMessage("", message, "user");
  userInput.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();

    setTimeout(() => {
      addMessage("Lira AI Assistant", data.reply, "bot");
      speakBot(data.reply);
    }, BOT_REPLY_DELAY);

  } catch {
    const errorReply = "Sorry, something went wrong!";
    addMessage("Lira AI Assistant", errorReply, "bot");
    speakBot(errorReply);
  }
}

// ------------------------------------
// Add message to chat
// ------------------------------------
function addMessage(sender, text, type) {
  const chatBox = document.getElementById("chat-box");

  const msg = document.createElement("div");
  msg.classList.add("message", type);

  const senderSpan = document.createElement("strong");
  senderSpan.innerText = sender;
  senderSpan.style.display = "block";

  const textSpan = document.createElement("span");
  textSpan.innerText = text;

  msg.appendChild(senderSpan);
  msg.appendChild(textSpan);
  chatBox.appendChild(msg);

  chatBox.scrollTop = chatBox.scrollHeight;
}

// ------------------------------------
// Speak bot reply
// ------------------------------------
function speakBot(text) {
  if (!("speechSynthesis" in window)) return;

  // Retry if voices not yet loaded
  if (!availableVoices.length) {
    setTimeout(() => speakBot(text), 200);
    return;
  }

  isBotSpeaking = true;
  recognition.stop();
  clearTimeout(silenceTimer);

  // Cancel current queue
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);

  // 🌸 Friendly young female voice selection
  const bestVoice =
    availableVoices.find(v => v.name.includes("Natural") && v.lang.startsWith("en")) ||
    availableVoices.find(v => v.name.includes("Google") && v.lang.startsWith("en")) ||
    availableVoices.find(v => v.name.includes("Female") && v.lang.startsWith("en")) ||
    availableVoices.find(v => v.lang.startsWith("en")) ||
    availableVoices[0];

  utterance.voice = bestVoice;
  utterance.lang = bestVoice.lang;

  // Friendly, youthful tone
  utterance.rate = 1.05;
  utterance.pitch = 1.25;
  utterance.volume = 1;

  utterance.onend = () => {
    isBotSpeaking = false;
    if (isConversationActive) {
      setTimeout(safeStartRecognition, LISTEN_RESTART_DELAY);
    }
  };

  utterance.onerror = (e) => {
    console.error("Speech synthesis error:", e);
    isBotSpeaking = false;
  };

  window.speechSynthesis.speak(utterance);
}
