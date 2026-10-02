from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agents import Runner
from Agent_com.main_agent import main_agent  # 👈 导入总指挥 Agent
from monitor_hook import MonitorHooks  # 👈 导入控制台监控钩子

class ChatRequest(BaseModel):
    message: str
    user_id: str = 'user'

app = FastAPI(title="旅游大师智能体")
monitor_hooks = MonitorHooks()

@app.get("/")
def home():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(req: ChatRequest):  # 👈 必须改为 async def
    print(f"后台收到数据 req.message={req.message}")
    
    try:
        # 👈 使用 await 调用智能体，并挂载监控钩子打印执行过程
        result = await Runner.run(main_agent, req.message, hooks=monitor_hooks)
        reply = result.final_output
    except Exception as e:
        print(f"Agent 运行错误: {e}")
        reply = f"抱歉，处理您的请求时出现了问题：{str(e)}"
        
    # 兼容前端 app.js 接收的 reply 字段
    return {"code": 200, "reply": reply, "data": reply}

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)