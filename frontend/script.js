const chatBox = document.getElementById("chat-box");
const questionInput = document.getElementById("question");
const sendButton = document.getElementById("send-button");

const API_URL = "/chat";


function addMessage(text, type) {

    const message = document.createElement("div");
    message.className = `message ${type}`;

    if (type === "assistant") {

        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = "LIA";

        message.appendChild(avatar);
    }

    const content = document.createElement("div");
    content.className = "message-content";

    if (type === "assistant") {

        const name = document.createElement("strong");
        name.textContent = "Lara Intelligent Assistant";

        content.appendChild(name);
    }

    const textElement = document.createElement("p");
    textElement.textContent = text;

    content.appendChild(textElement);

    message.appendChild(content);

    chatBox.appendChild(message);

    chatBox.scrollTop = chatBox.scrollHeight;
}


async function sendQuestion() {

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    addMessage(question, "user");

    questionInput.value = "";

    sendButton.disabled = true;
    sendButton.textContent = "Thinking...";

    try {

        const response = await fetch(API_URL, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })
        });

        if (!response.ok) {
            throw new Error("API request failed");
        }

        const data = await response.json();

        addMessage(
            data.answer,
            "assistant"
        );

    } catch (error) {

        console.error(error);

        addMessage(
            "Unable to connect to LIA. Make sure the FastAPI server is running.",
            "assistant"
        );

    } finally {

        sendButton.disabled = false;
        sendButton.textContent = "Send";
    }
}


sendButton.addEventListener("click", sendQuestion);


questionInput.addEventListener("keydown", function(event) {

    if (event.key === "Enter" && !event.shiftKey) {

        event.preventDefault();

        sendQuestion();
    }
});
