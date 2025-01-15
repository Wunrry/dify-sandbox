from fastapi import FastAPI, Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware  
from pydantic import BaseModel
from typing import Optional
import asyncio
from .executor import CodeExecutor
import os
import matplotlib.pyplot as plt
import io
from fastapi.responses import StreamingResponse


# 配置
API_KEY = os.getenv("API_KEY", "dify-sandbox")
MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "100"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))
WORKER_TIMEOUT = int(os.getenv("MAX_WORKERS", "15"))

app = FastAPI()
executor = CodeExecutor(timeout=WORKER_TIMEOUT, max_workers=MAX_WORKERS)

# 请求模型
class CodeRequest(BaseModel):
    language: str
    code: str
    preload: Optional[str] = ""
    enable_network: Optional[bool] = False
class PlotRequest(BaseModel):
    x: list
    y: list
    title: Optional[str] = "Plot"
    xlabel: Optional[str] = "X"
    ylabel: Optional[str] = "Y"
    
# 认证中间件
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/v1/sandbox"):
            api_key = request.headers.get("X-Api-Key")
            if not api_key or api_key != API_KEY:
                # 修改这里：返回 JSONResponse 而不是直接返回 HTTPException
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": -401,
                        "message": "Unauthorized",
                        "data": None
                    }
                )
        return await call_next(request)

# 并发控制中间件
class ConcurrencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.semaphore = asyncio.Semaphore(MAX_WORKERS)
        self.current_requests = 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/v1/sandbox/run"):
            if self.current_requests >= MAX_REQUESTS:
                return {
                    "code": -503,
                    "message": "Too many requests",
                    "data": None
                }
            
            self.current_requests += 1
            try:
                async with self.semaphore:
                    response = await call_next(request)
                return response
            finally:
                self.current_requests -= 1
        return await call_next(request)

# 添加中间件
app.add_middleware(AuthMiddleware)
app.add_middleware(ConcurrencyMiddleware)

@app.get("/health")
async def health_check():
    return "ok"

@app.post("/v1/sandbox/run")
async def execute_code(request: CodeRequest):
    if request.language not in ["python3", "nodejs"]:
        return {
            "code": -400,
            "message": "unsupported language",
            "data": None
        }

    result = await executor.execute(request.code, request.language)
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "error": result["error"] or "",
            "stdout": result["output"] or "",
        }
    }

@app.post("/v1/sandbox/plot")
async def generate_plot(request: PlotRequest):
    # 创建图像
    plt.figure()
    plt.plot(request.x, request.y)
    plt.title(request.title)
    plt.xlabel(request.xlabel)
    plt.ylabel(request.ylabel)
    
    # 将图像保存到字节流
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    
    # 返回图像
    return StreamingResponse(buf, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8194)