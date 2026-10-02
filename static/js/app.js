/**
 * AI旅游智能助手 前端交互
 * P1：视频同款布局 + Markdown 渲染 + 图片显示 + 回到底部
 * 会话数据暂存 localStorage（后端上下文隔离在 P2 实现）
 */
(function () {
  "use strict";

  var STORAGE_KEY = "travel_agent_sessions_v1";
  var TITLE_MAX = 14;

  var els = {
    newChatBtn: document.getElementById("new-chat-btn"),
    sessionList: document.getElementById("session-list"),
    chatBox: document.getElementById("chat-box"),
    scrollBottomBtn: document.getElementById("scroll-bottom-btn"),
    input: document.getElementById("message-input"),
    sendBtn: document.getElementById("send-btn"),
  };

  var state = {
    sessions: [],
    currentId: null,
  };

  function newId() {
    return "s_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7);
  }

  /* ---------- 本地持久化 ---------- */

  function save() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ sessions: state.sessions, currentId: state.currentId })
      );
    } catch (e) {
      console.warn("保存本地会话失败：", e);
    }
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.sessions) && parsed.sessions.length) {
          state.sessions = parsed.sessions;
          state.currentId = parsed.currentId || parsed.sessions[0].id;
          return;
        }
      }
    } catch (e) {
      console.warn("读取本地会话失败：", e);
    }
    state.sessions = [{ id: newId(), title: "新对话", messages: [] }];
    state.currentId = state.sessions[0].id;
    save();
  }

  /* ---------- 会话操作 ---------- */

  function currentSession() {
    for (var i = 0; i < state.sessions.length; i++) {
      if (state.sessions[i].id === state.currentId) return state.sessions[i];
    }
    return null;
  }

  function createSession() {
    var session = { id: newId(), title: "新对话", messages: [] };
    state.sessions.unshift(session);
    state.currentId = session.id;
    save();
    renderSessions();
    renderMessages();
    return session;
  }

  function switchSession(id) {
    if (state.currentId === id) return;
    state.currentId = id;
    save();
    renderSessions();
    renderMessages();
  }

  function makeTitle(text) {
    var t = text.replace(/\s+/g, " ").trim();
    return t.length > TITLE_MAX ? t.slice(0, TITLE_MAX) + "..." : t;
  }

  /* ---------- 渲染 ---------- */

  function renderSessions() {
    els.sessionList.innerHTML = "";
    state.sessions.forEach(function (session) {
      var item = document.createElement("div");
      item.className = "session-item" + (session.id === state.currentId ? " active" : "");
      item.textContent = session.title;
      item.title = session.title;
      item.addEventListener("click", function () {
        switchSession(session.id);
      });
      els.sessionList.appendChild(item);
    });
  }

  function createBubble(role, text) {
    var bubble = document.createElement("div");
    bubble.className = "message " + role;
    if (role === "bot") {
      bubble.innerHTML = MarkdownRenderer.render(text);
      if (bubble.querySelector("table")) bubble.classList.add("wide");
    } else {
      bubble.textContent = text;
    }
    return bubble;
  }

  function scrollToBottom() {
    els.chatBox.scrollTop = els.chatBox.scrollHeight;
  }

  function renderMessages() {
    var session = currentSession();
    els.chatBox.innerHTML = "";
    if (!session) return;
    session.messages.forEach(function (msg) {
      els.chatBox.appendChild(createBubble(msg.role, msg.content));
    });
    scrollToBottom();
  }

  function appendBubble(role, text) {
    var bubble = createBubble(role, text);
    els.chatBox.appendChild(bubble);
    scrollToBottom();
    return bubble;
  }

  function setSending(sending) {
    els.sendBtn.disabled = sending;
    els.sendBtn.textContent = sending ? "规划中" : "发送";
  }

  /* ---------- 发送消息 ---------- */

  async function sendMessage() {
    var text = els.input.value.trim();
    if (!text) return;

    var session = currentSession() || createSession();

    if (session.messages.length === 0) {
      session.title = makeTitle(text);
      renderSessions();
    }

    session.messages.push({ role: "user", content: text });
    appendBubble("user", text);
    els.input.value = "";
    save();

    var loading = appendBubble("bot", "正在规划中...");
    loading.classList.add("thinking");
    setSending(true);

    try {
      var response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, user_id: "user_001", session_id: session.id }),
      });
      if (!response.ok) throw new Error("服务器错误：" + response.status);

      var data = await response.json();
      var reply = (data && (data.reply || data.data)) || "抱歉，我没有收到有效回复。";

      session.messages.push({ role: "bot", content: reply });
      loading.classList.remove("thinking");
      loading.innerHTML = MarkdownRenderer.render(reply);
      if (loading.querySelector("table")) loading.classList.add("wide");
      save();
    } catch (error) {
      console.error("请求失败：", error);
      var errText = "网络连接失败，请检查后端服务是否启动。";
      session.messages.push({ role: "bot", content: errText });
      loading.classList.remove("thinking");
      loading.textContent = errText;
      save();
    } finally {
      setSending(false);
      scrollToBottom();
    }
  }

  /* ---------- 事件绑定 ---------- */

  els.newChatBtn.addEventListener("click", function () {
    createSession();
    els.input.focus();
  });

  els.sendBtn.addEventListener("click", sendMessage);

  els.input.addEventListener("keydown", function (e) {
    // isComposing：避免中文输入法选词回车被误判为发送
    if (e.key === "Enter" && !e.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  });

  els.chatBox.addEventListener("scroll", function () {
    var distance = els.chatBox.scrollHeight - els.chatBox.scrollTop - els.chatBox.clientHeight;
    els.scrollBottomBtn.classList.toggle("visible", distance > 60);
  });

  els.scrollBottomBtn.addEventListener("click", scrollToBottom);

  /* ---------- 启动 ---------- */

  load();
  renderSessions();
  renderMessages();
  els.input.focus();
})();
