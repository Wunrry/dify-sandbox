from fastapi import FastAPI, Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware  
from pydantic import BaseModel
from typing import Optional
import asyncio
from .executor import CodeExecutor
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import io
from fastapi.responses import StreamingResponse
import pandas as pd  
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    width: Optional[float] = 12                  # 图表宽度
    height: Optional[float] = 6                 # 图表高度

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
    width: Optional[float] = 12                  # 图表宽度
    height: Optional[float] = 6                 # 图表高度
    
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
        # 打印当前工作目录和文件路径
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Reading CSV file: {request.file_path}")
        
        # 读取 CSV 文件
        df = pd.read_csv(request.file_path, sep=',', encoding='utf-8')
        logger.info(f"CSV columns: {df.columns}")
        
        # 检查指定的列是否存在
        if request.x_column not in df.columns or request.y_column not in df.columns:
            logger.error(f"Specified columns not found: x_column={request.x_column}, y_column={request.y_column}")
            return {
                "code": -400,
                "message": "Specified columns not found in CSV file",
                "data": None
            }
        
        # 提取 X 和 Y 列数据
        try:
            # 尝试将 x_column 转换为 datetime 类型
            x = pd.to_datetime(df[request.x_column], errors='coerce')
            if x.isnull().all():  # 如果全部转换失败，说明不是时间格式
                logger.info(f"x_column is not a datetime format, trying numeric...")
                x = pd.to_numeric(df[request.x_column], errors='coerce')  # 尝试转换为数值类型
                if x.isnull().all():  # 如果仍然全部转换失败，说明是字符串格式
                    logger.info(f"x_column is not numeric, treating as string/categorical.")
                    x = df[request.x_column].astype(str)  # 直接使用字符串格式
            y = pd.to_numeric(df[request.y_column], errors='coerce')  # 转换为数值类型
        except Exception as e:
            logger.error(f"Failed to convert columns: {str(e)}")
            return {
                "code": -400,
                "message": f"Failed to convert columns: {str(e)}",
                "data": None
            }
        
        # 检查是否有无效值
        if x.isnull().any() or y.isnull().any():
            logger.warning(f"Invalid values found in x_column or y_column. Rows with NaN/NaT will be dropped.")
            df_cleaned = df.dropna(subset=[request.x_column, request.y_column])  # 删除包含 NaN/NaT 的行
            x = df_cleaned[request.x_column]
            y = pd.to_numeric(df_cleaned[request.y_column])
        
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
        
        # 根据 x_column 的数据类型调整 X 轴格式
        if pd.api.types.is_datetime64_any_dtype(x):  # 如果是时间格式
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))  # 设置日期格式
            plt.gcf().autofmt_xdate()  # 自动旋转日期标签
        elif pd.api.types.is_numeric_dtype(x):  # 如果是数值格式
            pass  # 无需特殊处理
        else:  # 如果是字符串/分类格式
            plt.xticks(rotation=45)  # 旋转 X 轴标签，避免重叠
        
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
        logger.error(f"CSV file not found: {request.file_path}")
        return {
            "code": -404,
            "message": "CSV file not found",
            "data": None
        }
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return {
            "code": -500,
            "message": f"An error occurred: {str(e)}",
            "data": None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8194)