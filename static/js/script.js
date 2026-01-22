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
  } catch (err) {
    console.error("Error:", err);
    addMessage("Lira AI Assistant", "Sorry, something went wrong!", "bot");
  }
}

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
