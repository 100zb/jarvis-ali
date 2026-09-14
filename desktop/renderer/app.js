(() => {
  "use strict";

  const HTTP_BASE = "http://127.0.0.1:8756";
  const WS_URL = "ws://127.0.0.1:8756/ws/chat";
  const RECONNECT_DELAY_MS = 1200;

  const $ = (id) => document.getElementById(id);
  const messagesEl = $("messages");
  const chatScroll = $("chat-scroll");
  const emptyState = $("empty-state");
  const form = $("composer-form");
  const input = $("composer-input");
  const sendBtn = $("send-btn");
  const statusDot = $("status-dot");
  const statusLabel = $("status-label");
  const toolsList = $("tools-list");
  const resetBtn = $("reset-btn");
  const statMessages = $("stat-messages");
  const statTurns = $("stat-turns");
  const statCompactions = $("stat-compactions");

  let ws = null;
  let connected = false;
  let streaming = false;
  let currentAssistantBubble = null;
  let currentAssistantText = "";

  // ---------- markdown (subset) ----------

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderMarkdown(raw) {
    let text = escapeHtml(raw);
    text = text.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/(^|\s)\*([^*\n]+)\*(?=\s|$)/g, "$1<em>$2</em>");
    return text;
  }

  // ---------- rendering ----------

  function scrollToBottom(smooth = true) {
    chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  }

  function hideEmptyState() {
    if (emptyState) emptyState.style.display = "none";
  }

  function addUserMessage(text) {
    hideEmptyState();
    const row = document.createElement("div");
    row.className = "msg msg-user";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollToBottom();
  }

  function addToolChip(name, pending) {
    hideEmptyState();
    const row = document.createElement("div");
    row.className = "tool-chip-row";
    row.dataset.tool = name;
    const chip = document.createElement("div");
    chip.className = "tool-chip" + (pending ? " pending" : "");
    chip.innerHTML = `<span class="tool-dot"></span>${escapeHtml(name)}(...)`;
    row.appendChild(chip);
    messagesEl.appendChild(row);
    scrollToBottom();
    return row;
  }

  function resolveToolChip(row) {
    const chip = row.querySelector(".tool-chip");
    if (chip) chip.classList.remove("pending");
  }

  function startAssistantMessage() {
    hideEmptyState();
    const row = document.createElement("div");
    row.className = "msg msg-assistant";
    const bubble = document.createElement("div");
    bubble.className = "bubble typing";
    bubble.innerHTML = "<span></span><span></span><span></span>";
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollToBottom();
    currentAssistantBubble = bubble;
    currentAssistantText = "";
  }

  function appendAssistantDelta(delta) {
    if (!currentAssistantBubble) startAssistantMessage();
    if (currentAssistantBubble.classList.contains("typing")) {
      currentAssistantBubble.classList.remove("typing");
      currentAssistantBubble.innerHTML = "";
    }
    currentAssistantText += delta;
    currentAssistantBubble.innerHTML = renderMarkdown(currentAssistantText);
    scrollToBottom();
  }

  function finishAssistantMessage(finalText) {
    if (!currentAssistantBubble) startAssistantMessage();
    currentAssistantBubble.classList.remove("typing");
    currentAssistantBubble.innerHTML = renderMarkdown(finalText || currentAssistantText || "...");
    currentAssistantBubble = null;
    currentAssistantText = "";
    scrollToBottom();
  }

  // ---------- connection state ----------

  function setStatus(state, label) {
    statusDot.className = "status-dot" + (state ? ` ${state}` : "");
    statusLabel.textContent = label;
  }

  function setStreaming(isStreaming) {
    streaming = isStreaming;
    sendBtn.disabled = isStreaming || input.value.trim().length === 0;
    input.disabled = isStreaming;
  }

  // ---------- backend info ----------

  async function loadTools() {
    try {
      const res = await fetch(`${HTTP_BASE}/api/tools`);
      const data = await res.json();
      toolsList.innerHTML = "";
      (data.tools || []).forEach((name) => {
        const pill = document.createElement("div");
        pill.className = "tool-pill";
        pill.textContent = name;
        toolsList.appendChild(pill);
      });
    } catch (e) {
      // backend pas encore pret, on reessaiera a la prochaine connexion
    }
  }

  let historyLoaded = false;

  async function loadHistory() {
    if (historyLoaded) return;
    historyLoaded = true;
    try {
      const res = await fetch(`${HTTP_BASE}/api/history`);
      const data = await res.json();
      const msgs = data.messages || [];
      if (msgs.length === 0) return;

      hideEmptyState();
      msgs.forEach((m) => {
        const row = document.createElement("div");
        row.className = `msg msg-${m.role === "user" ? "user" : "assistant"}`;
        const bubble = document.createElement("div");
        bubble.className = "bubble";
        if (m.role === "user") {
          bubble.textContent = m.content;
        } else {
          bubble.innerHTML = renderMarkdown(m.content);
        }
        row.appendChild(bubble);
        messagesEl.appendChild(row);
      });
      scrollToBottom(false);
    } catch (e) {
      historyLoaded = false; // on reessaiera a la prochaine connexion
    }
  }

  async function loadStats() {
    try {
      const res = await fetch(`${HTTP_BASE}/api/stats`);
      const data = await res.json();
      statMessages.textContent = data.messages ?? 0;
      statTurns.textContent = data.turns ?? 0;
      statCompactions.textContent = data.compactions ?? 0;
    } catch (e) {
      // ignore
    }
  }

  // ---------- websocket ----------

  let reconnectAttempts = 0;

  function connect() {
    setStatus("", "Connexion...");
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      connected = true;
      reconnectAttempts = 0;
      setStatus("online", "En ligne");
      setStreaming(false);
      loadTools();
      loadStats();
      loadHistory();
    };

    ws.onclose = () => {
      connected = false;
      reconnectAttempts += 1;
      // Apres plusieurs echecs, le backend ne demarre probablement pas du tout
      // (cle API manquante, uv absent...) plutot qu'un simple probleme reseau.
      setStatus("error", reconnectAttempts >= 4 ? "Backend indisponible" : "Deconnecte");
      setStreaming(true); // bloque l'envoi tant qu'on n'est pas reconnecte
      setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleEvent(data);
    };
  }

  let pendingToolChip = null;

  function discardTypingPlaceholder() {
    if (currentAssistantBubble && currentAssistantBubble.classList.contains("typing")) {
      currentAssistantBubble.closest(".msg").remove();
      currentAssistantBubble = null;
      currentAssistantText = "";
    }
  }

  function handleEvent(event) {
    switch (event.type) {
      case "delta":
        appendAssistantDelta(event.content);
        break;
      case "tool_call":
        discardTypingPlaceholder();
        pendingToolChip = addToolChip(event.name, true);
        break;
      case "tool_result":
        if (pendingToolChip) resolveToolChip(pendingToolChip);
        pendingToolChip = null;
        if (!currentAssistantBubble) startAssistantMessage();
        break;
      case "done":
        finishAssistantMessage(event.content);
        setStreaming(false);
        loadStats();
        break;
      case "compacted":
        loadStats();
        break;
      case "error":
        finishAssistantMessage(`Erreur : ${event.message}`);
        setStreaming(false);
        break;
    }
  }

  // ---------- composer ----------

  function autoResize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  input.addEventListener("input", () => {
    autoResize();
    sendBtn.disabled = streaming || input.value.trim().length === 0;
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || streaming || !connected) return;

    addUserMessage(text);
    ws.send(JSON.stringify({ message: text }));

    input.value = "";
    autoResize();
    setStreaming(true);
    startAssistantMessage();
  });

  resetBtn.addEventListener("click", async () => {
    try {
      await fetch(`${HTTP_BASE}/api/reset`, { method: "POST" });
      messagesEl.innerHTML = "";
      if (emptyState) emptyState.style.display = "";
      loadStats();
    } catch (e) {
      // ignore
    }
  });

  connect();
})();
