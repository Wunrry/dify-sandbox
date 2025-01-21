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
import pandas as pd  
from enum import Enum

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

# 定义图表类型枚举
class PlotType(str, Enum):
    LINE = "line"       # 折线图
    SCATTER = "scatter" # 散点图
    BAR = "bar"         # 柱状图

# 定义线型枚举
class LineStyle(str, Enum):
    SOLID = "-"         # 实线
    DASHED = "--"       # 虚线
    DOTTED = ":"        # 点线
    DASHDOT = "-."      # 点划线

# 定义点型枚举
class MarkerStyle(str, Enum):
    CIRCLE = "o"        # 圆圈
    SQUARE = "s"        # 正方形
    TRIANGLE = "^"      # 三角形
    STAR = "*"          # 星号

# 定义图例位置枚举
class LegendLocation(str, Enum):
    BEST = "best"       # 自动选择最佳位置
    UPPER_RIGHT = "upper right"
    UPPER_LEFT = "upper left"
    LOWER_RIGHT = "lower right"
    LOWER_LEFT = "lower left"
    RIGHT = "right"
    CENTER = "center"
    LEFT = "left"

class PlotRequest(BaseModel):
    x: list
    y: list
    title: Optional[str] = "Plot"
    xlabel: Optional[str] = "X"
    ylabel: Optional[str] = "Y"
    plot_type: Optional[PlotType] = PlotType.LINE  # 图表类型，默认为折线图
    color: Optional[str] = "blue"                 # 线条或点的颜色
    line_style: Optional[LineStyle] = LineStyle.SOLID  # 线型，默认为实线
    marker_style: Optional[MarkerStyle] = None    # 点型，默认为无
    grid: Optional[bool] = False                  # 是否显示网格，默认为 False
    legend: Optional[bool] = False                # 是否显示图例，默认为 False
    legend_location: Optional[LegendLocation] = LegendLocation.BEST  # 图例位置
    width: Optional[float] = 6.4                  # 图表宽度，默认 6.4 英寸
    height: Optional[float] = 4.8                 # 图表高度，默认 4.8 英寸

class CSVPlotRequest(BaseModel):
    file_path: str
    x_column: str
    y_column: str
    title: Optional[str] = "CSV Plot"
    xlabel: Optional[str] = "X"
    ylabel: Optional[str] = "Y"
    plot_type: Optional[PlotType] = PlotType.LINE  # 图表类型，默认为折线图
    color: Optional[str] = "blue"                 # 线条或点的颜色
    line_style: Optional[LineStyle] = LineStyle.SOLID  # 线型，默认为实线
    marker_style: Optional[MarkerStyle] = None    # 点型，默认为无
    grid: Optional[bool] = False                  # 是否显示网格，默认为 False
    legend: Optional[bool] = False                # 是否显示图例，默认为 False
    legend_location: Optional[LegendLocation] = LegendLocation.BEST  # 图例位置
    width: Optional[float] = 6.4                  # 图表宽度，默认 6.4 英寸
    height: Optional[float] = 4.8                 # 图表高度，默认 4.8 英寸
    
# 认证中间件
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/v1/sandbox"):
            api_key = request.headers.get("X-Api-Key")
            if not api_key or api_key != API_KEY:
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

@app.post("/v1/sandbox/jsonplot")
async def generate_plot(request: PlotRequest):
    # 设置图表尺寸
    plt.figure(figsize=(request.width, request.height))
    
    # 根据图表类型绘制
    if request.plot_type == PlotType.LINE:
        plt.plot(
            request.x, request.y,
            color=request.color,
            linestyle=request.line_style.value,
            marker=request.marker_style.value if request.marker_style else None,
            label="Line"
        )
    elif request.plot_type == PlotType.SCATTER:
        plt.scatter(
            request.x, request.y,
            color=request.color,
            marker=request.marker_style.value if request.marker_style else "o",
            label="Scatter"
        )
    elif request.plot_type == PlotType.BAR:
        plt.bar(
            request.x, request.y,
            color=request.color,
            label="Bar"
        )
    
    # 设置标题和标签
    plt.title(request.title)
    plt.xlabel(request.xlabel)
    plt.ylabel(request.ylabel)
    
    # 显示网格
    if request.grid:
        plt.grid(True)
    
    # 显示图例
    if request.legend:
        plt.legend(loc=request.legend_location.value)
    
    # 将图像保存到字节流
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    
    # 返回图像
    return StreamingResponse(buf, media_type="image/png")

@app.post("/v1/sandbox/csvplot")
async def generate_csv_plot(request: CSVPlotRequest):
    try:
        # 读取 CSV 文件
        df = pd.read_csv(request.file_path)
        
        # 检查指定的列是否存在
        if request.x_column not in df.columns or request.y_column not in df.columns:
            return {
                "code": -400,
                "message": "Specified columns not found in CSV file",
                "data": None
            }
        
        # 提取 X 和 Y 列数据
        x = df[request.x_column]
        y = df[request.y_column]
        
        # 设置图表尺寸
        plt.figure(figsize=(request.width, request.height))
        
        # 根据图表类型绘制
        if request.plot_type == PlotType.LINE:
            plt.plot(
                x, y,
                color=request.color,
                linestyle=request.line_style.value,
                marker=request.marker_style.value if request.marker_style else None,
                label="Line"
            )
        elif request.plot_type == PlotType.SCATTER:
            plt.scatter(
                x, y,
                color=request.color,
                marker=request.marker_style.value if request.marker_style else "o",
                label="Scatter"
            )
        elif request.plot_type == PlotType.BAR:
            plt.bar(
                x, y,
                color=request.color,
                label="Bar"
            )
        
        # 设置标题和标签
        plt.title(request.title)
        plt.xlabel(request.xlabel)
        plt.ylabel(request.ylabel)
        
        # 显示网格
        if request.grid:
            plt.grid(True)
        
        # 显示图例
        if request.legend:
            plt.legend(loc=request.legend_location.value)
        
        # 将图像保存到字节流
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        
        # 返回图像
        return StreamingResponse(buf, media_type="image/png")
    
    except FileNotFoundError:
        return {
            "code": -404,
            "message": "CSV file not found",
            "data": None
        }
    except Exception as e:
        return {
            "code": -500,
            "message": f"An error occurred: {str(e)}",
            "data": None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8194)