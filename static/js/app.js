document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("send-btn");
    const messageInput = document.getElementById("message-input");
    const chatBox = document.getElementById("chat-box");

    // 添加消息到对话框的函数
    function addMessage(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}`;
        msgDiv.textContent = text;
        chatBox.appendChild(msgDiv);
        // 自动滚动到底部
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // 发送消息的核心函数
    async function sendMessage() {
        const text = messageInput.value.trim();
        if (!text) return; // 如果为空则不发送

        // 1. 在界面显示用户的消息
        addMessage(text, "user");
        messageInput.value = ""; // 清空输入框

        // 2. 显示一个临时的“思考中”提示
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "message bot";
        loadingDiv.textContent = "正在规划中...";
        chatBox.appendChild(loadingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            // 3. 发送请求给 FastAPI 后端
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: text,
                    user_id: "user_001" // 你的后端默认是 'user'，这里也可以传自定义
                })
            });

            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }

            // 4. 解析后端返回的 JSON
            const data = await response.json();
            
            // 移除“正在规划中”的提示
            chatBox.removeChild(loadingDiv);
            
            // 显示后端的回复
            addMessage(data.reply || "抱歉，我没有收到有效回复。", "bot");

        } catch (error) {
            console.error("请求失败:", error);
            chatBox.removeChild(loadingDiv);
            addMessage("网络连接失败，请检查后端服务是否启动。", "bot");
        }
    }

    // 绑定点击事件
    sendBtn.addEventListener("click", sendMessage);

    // 绑定回车键发送
    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage();
        }
    });
});