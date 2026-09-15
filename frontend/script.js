const ADMIN_TOKEN_KEY = "lia_admin_token";
const routes = document.querySelectorAll("[data-route]");

function currentRoute() {
    const value = window.location.hash.replace(/^#\/?/, "");
    return ["chat", "admin"].includes(value) ? value : "home";
}

function navigate() {
    const route = currentRoute();
    routes.forEach((section) => {
        section.hidden = section.dataset.route !== route;
    });
    document.querySelectorAll("[data-route-link]").forEach((link) => {
        link.classList.toggle("active", link.dataset.routeLink === route);
    });
    if (route === "admin") {
        renderAdminState();
    }
}

window.addEventListener("hashchange", navigate);
navigate();

const chatBox = document.getElementById("chat-box");
const questionInput = document.getElementById("question");
const chatForm = document.getElementById("chat-form");
const sendButton = document.getElementById("send-button");

function addMessage(text, type) {
    const message = document.createElement("div");
    message.className = `message message-${type}`;

    if (type === "assistant") {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = "✦";
        message.appendChild(avatar);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (type === "assistant") {
        const name = document.createElement("strong");
        name.textContent = "LIA";
        bubble.appendChild(name);
    }
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
    message.appendChild(bubble);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addAssistantResponse(data) {
    const message = document.createElement("div");
    message.className = "message message-assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "✦";
    message.appendChild(avatar);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    const name = document.createElement("strong");
    name.textContent = "LIA";
    bubble.appendChild(name);

    if (data.answer) {
        const answer = document.createElement("div");
        answer.className = "rich-answer";
        answer.innerHTML = renderAssistantText(data.answer);
        bubble.appendChild(answer);
    }

    if (data.table) {
        const tableTitle = document.createElement("h4");
        tableTitle.textContent = data.table.title;
        bubble.appendChild(tableTitle);

        const tableWrap = document.createElement("div");
        tableWrap.className = "answer-table-wrap";
        const table = document.createElement("table");
        const head = document.createElement("thead");
        const headRow = document.createElement("tr");
        data.table.columns.forEach((column) => {
            const cell = document.createElement("th");
            cell.textContent = column;
            headRow.appendChild(cell);
        });
        head.appendChild(headRow);
        table.appendChild(head);

        const body = document.createElement("tbody");
        data.table.rows.forEach((row) => {
            const tableRow = document.createElement("tr");
            row.forEach((value) => {
                const cell = document.createElement("td");
                cell.textContent = value;
                tableRow.appendChild(cell);
            });
            body.appendChild(tableRow);
        });
        table.appendChild(body);
        tableWrap.appendChild(table);
        bubble.appendChild(tableWrap);
    }

    message.appendChild(bubble);
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
    if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise([bubble]);
    }
}

function renderAssistantText(text) {
    const mathBlocks = [];
    const escaped = escapeHtml(text).replace(/\\\[([\s\S]*?)\\\]/g, (_, formula) => {
        const index = mathBlocks.push(formatMath(formula)) - 1;
        return `@@MATH_${index}@@`;
    });
    const lines = escaped.split("\n");
    const rendered = [];
    let inList = false;

    lines.forEach((line) => {
        const listItem = line.match(/^\s*[-*]\s+(.+)$/);
        if (listItem) {
            if (!inList) {
                rendered.push("<ul>");
                inList = true;
            }
            rendered.push(`<li>${formatInline(listItem[1], mathBlocks)}</li>`);
            return;
        }
        if (inList) {
            rendered.push("</ul>");
            inList = false;
        }
        if (line.trim()) {
            rendered.push(`<p>${formatInline(line, mathBlocks)}</p>`);
        }
    });
    if (inList) rendered.push("</ul>");
    return rendered.join("");
}

function formatInline(text, mathBlocks) {
    return text
        .replace(/@@MATH_(\d+)@@/g, (_, index) => `<span class="math-fallback">${mathBlocks[index]}</span>`)
        .replace(/\\\(([\s\S]*?)\\\)/g, (_, formula) => `<span class="math-fallback">${formatMath(formula)}</span>`)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/__(.+?)__/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function formatMath(formula) {
    return formula
        .replace(/\\text\{([^{}]*)\}/g, "$1")
        .replace(/\\times/g, " × ")
        .replace(/\\left|\\right/g, "")
        .replace(/\\,/g, " ")
        .replace(/[{}]/g, "")
        .replace(/\s+/g, " ")
        .trim();
}

function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    }[character]));
}

function addTypingIndicator() {
    const message = document.createElement("div");
    message.id = "typing-indicator";
    message.className = "message message-assistant";
    message.innerHTML = `
        <div class="avatar">✦</div>
        <div class="bubble">
            <strong>LIA</strong>
            <div class="typing-dots" aria-label="LIA is thinking">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendQuestion(question) {
    const value = (question || questionInput.value).trim();
    if (!value) return;

    addMessage(value, "user");
    questionInput.value = "";
    sendButton.disabled = true;
    addTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: value}),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Request failed");
        document.getElementById("typing-indicator")?.remove();
        addAssistantResponse(data);
    } catch (error) {
        document.getElementById("typing-indicator")?.remove();
        addMessage("I couldn't connect right now. Please try again.", "assistant");
    } finally {
        sendButton.disabled = false;
    }
}

chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    sendQuestion();
});

questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
});

document.querySelectorAll(".quick-questions button").forEach((button) => {
    button.addEventListener("click", () => sendQuestion(button.textContent));
});

function adminHeaders() {
    return {Authorization: `Bearer ${localStorage.getItem(ADMIN_TOKEN_KEY)}`};
}

function renderAdminState() {
    const loggedIn = Boolean(localStorage.getItem(ADMIN_TOKEN_KEY));
    document.getElementById("admin-login").hidden = loggedIn;
    document.getElementById("admin-dashboard").hidden = !loggedIn;
    if (loggedIn) loadDocuments();
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("login-error");
    error.textContent = "";

    try {
        const response = await fetch("/admin/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                admin_id: document.getElementById("admin-id").value.trim(),
                password: document.getElementById("admin-password").value,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to sign in");
        localStorage.setItem(ADMIN_TOKEN_KEY, data.token);
        renderAdminState();
    } catch (err) {
        error.textContent = err.message;
    }
});

async function loadDocuments() {
    const response = await fetch("/admin/documents", {headers: adminHeaders()});
    if (response.status === 401) {
        localStorage.removeItem(ADMIN_TOKEN_KEY);
        renderAdminState();
        return;
    }
    if (!response.ok) throw new Error("Unable to load documents");

    const data = await response.json();
    const documents = data.documents || [];
    document.getElementById("document-count").textContent = `${documents.length} document${documents.length === 1 ? "" : "s"}`;
    document.getElementById("chunk-count").textContent = documents.reduce((total, item) => total + item.chunks, 0);
    const list = document.getElementById("document-list");
    list.innerHTML = documents.length
        ? documents.map((item) => `
            <div class="document-row">
                <span class="file-icon">PDF</span>
                <span><strong>${escapeHtml(item.filename)}</strong><small>${item.chunks} chunks · ${formatBytes(item.size)}</small></span>
                <span class="document-live">●</span>
            </div>`).join("")
        : "<p class='form-message'>No documents uploaded yet.</p>";
}

document.getElementById("pdf-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const status = document.getElementById("upload-status");
    status.className = "form-message";
    status.style.color = "var(--blue)";
    status.textContent = "Uploading and indexing…";

    const formData = new FormData();
    formData.append("file", file);
    try {
        const response = await fetch("/admin/documents/upload", {
            method: "POST",
            headers: adminHeaders(),
            body: formData,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Upload failed");
        status.style.color = "var(--green)";
        status.textContent = `${data.filename} is ready. ${data.chunks} chunks indexed.`;
        await loadDocuments();
    } catch (error) {
        status.style.color = "var(--danger)";
        status.textContent = error.message;
    } finally {
        event.target.value = "";
    }
});

document.getElementById("refresh-documents").addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    try {
        await loadDocuments();
    } finally {
        event.currentTarget.disabled = false;
    }
});

document.getElementById("logout-admin").addEventListener("click", () => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    renderAdminState();
});

function formatBytes(bytes) {
    return bytes < 1024 * 1024
        ? `${Math.max(1, Math.round(bytes / 1024))} KB`
        : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
