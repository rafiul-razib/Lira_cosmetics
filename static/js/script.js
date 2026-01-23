// ------------------------------------
// Send message function
// ------------------------------------
async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  // Add user message
  addMessage("", message, "user");
  input.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();

    // Add bot reply
    addMessage("Lira AI Assistant", data.reply, "bot");

    // Speak bot reply
    speakBot(data.reply);
  } catch (err) {
    console.error("Error:", err);
    const errorReply = "Sorry, something went wrong!";
    addMessage("Lira AI Assistant", errorReply, "bot");
    speakBot(errorReply);
  }
}

// ------------------------------------
// Add message to chat box
// ------------------------------------
function addMessage(sender, text, type) {
  const chatBox = document.getElementById("chat-box");

  // Create message container
  const msg = document.createElement("div");
  msg.classList.add("message", type); // Adds both "message" and "user"/"bot" class

  // Create sender label
  const senderSpan = document.createElement("strong");
  senderSpan.innerText = `${sender} `;
  senderSpan.style.display = "block";
  senderSpan.style.marginBottom = "4px";

  // Create message text
  const textSpan = document.createElement("span");
  textSpan.innerText = text;

  // Append sender and text to message
  msg.appendChild(senderSpan);
  msg.appendChild(textSpan);

  // Append message to chat box
  chatBox.appendChild(msg);

  // Smooth scroll to bottom
  chatBox.scrollTo({
    top: chatBox.scrollHeight,
    behavior: "smooth"
  });
}

// ------------------------------------
// Speak bot reply with female voice
// ------------------------------------
function speakBot(text) {
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);

    // Get voices
    const voices = window.speechSynthesis.getVoices();

    // Select a female voice (example: Google UK English Female)
    const bestVoice = voices.find(v => v.name.includes("Natural") && v.lang.startsWith("en")) || 
                  voices.find(v => v.name.includes("Google") && v.lang.startsWith("en")) ||
                  voices.find(v => v.name.includes("Female") && v.lang.startsWith("en")) ||
      voices[0];
    
    utterance.voice = bestVoice;

    // Set friendly speech parameters
    utterance.lang = bestVoice.lang || "en-US";
    utterance.rate = 0.8;    // Normal speed
    utterance.pitch = 1.3; // Slightly higher pitch for friendly tone
    utterance.volume = 0.9;  // Max volume

    window.speechSynthesis.speak(utterance);
  }
}

// ------------------------------------
// Optional: reload voices if not loaded initially
// ------------------------------------
window.speechSynthesis.onvoiceschanged = () => {
  console.log("Available voices:", window.speechSynthesis.getVoices());
};
