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
from matplotlib.font_manager import FontProperties

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Noto Sans CJK', 'WenQuanYi Zen Hei']  # 设置支持中文的字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

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

class DoubleLinePlotRequest(BaseModel):
    file_path: str
    x_column: str
    y1_column: str  # 第一个 Y 轴数据列
    y2_column: str  # 第二个 Y 轴数据列
    title: Optional[str] = "Double Line Plot"
    xlabel: Optional[str] = "X"
    y1_label: Optional[str] = "Y1"  # 第一个 Y 轴标签
    y2_label: Optional[str] = "Y2"  # 第二个 Y 轴标签
    plot_type: Optional[PlotType] = PlotType.LINE  # 图表类型，默认为折线图
    color1: Optional[str] = "blue"  # 第一条线的颜色
    color2: Optional[str] = "red"   # 第二条线的颜色
    line_style1: Optional[LineStyle] = LineStyle.SOLID  # 第一条线的线型
    line_style2: Optional[LineStyle] = LineStyle.SOLID  # 第二条线的线型
    marker_style1: Optional[MarkerStyle] = None  # 第一条线的点型
    marker_style2: Optional[MarkerStyle] = None  # 第二条线的点型
    grid: Optional[bool] = False  # 是否显示网格
    legend: Optional[bool] = False  # 是否显示图例
    legend_location: Optional[LegendLocation] = LegendLocation.BEST  # 图例位置
    width: Optional[float] = 12  # 图表宽度
    height: Optional[float] = 6  # 图表高度

class CombinedYPlotRequest(BaseModel):
    file_path: str
    x_column: str
    y_columns: list[str]  # 用于计算 Y 轴数据的字段列表
    constants: dict[str, float]  # 用于计算的常量，例如 {"P0": 100, "d_tbm": 0.5}
    title: Optional[str] = "Combined Y Plot"
    xlabel: Optional[str] = "X"
    ylabel: Optional[str] = "Y"
    plot_type: Optional[PlotType] = PlotType.LINE  # 图表类型，默认为折线图
    color: Optional[str] = "blue"  # 线条或点的颜色
    line_style: Optional[LineStyle] = LineStyle.SOLID  # 线型，默认为实线
    marker_style: Optional[MarkerStyle] = None  # 点型，默认为无
    grid: Optional[bool] = False  # 是否显示网格
    legend: Optional[bool] = False  # 是否显示图例
    legend_location: Optional[LegendLocation] = LegendLocation.BEST  # 图例位置
    width: Optional[float] = 12  # 图表宽度
    height: Optional[float] = 6  # 图表高度

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
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))  # 设置日期格式  '%Y-%m-%d %H:%M:%S'
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

@app.post("/v1/sandbox/csvplot/ms")
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
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))  # 设置日期格式  '%Y-%m-%d %H:%M:%S'
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


@app.post("/v1/sandbox/doublelineplot")
async def generate_double_line_plot(request: DoubleLinePlotRequest):
    try:
        # 打印当前工作目录和文件路径
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Reading CSV file: {request.file_path}")
        
        # 读取 CSV 文件
        df = pd.read_csv(request.file_path, sep=',', encoding='utf-8')
        logger.info(f"CSV columns: {df.columns}")
        
        # 检查指定的列是否存在
        if (request.x_column not in df.columns or 
            request.y1_column not in df.columns or 
            request.y2_column not in df.columns):
            logger.error(f"Specified columns not found: x_column={request.x_column}, y1_column={request.y1_column}, y2_column={request.y2_column}")
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
            y1 = pd.to_numeric(df[request.y1_column], errors='coerce')  # 转换为数值类型
            y2 = pd.to_numeric(df[request.y2_column], errors='coerce')  # 转换为数值类型
        except Exception as e:
            logger.error(f"Failed to convert columns: {str(e)}")
            return {
                "code": -400,
                "message": f"Failed to convert columns: {str(e)}",
                "data": None
            }
        
        # 检查是否有无效值
        if x.isnull().any() or y1.isnull().any() or y2.isnull().any():
            logger.warning(f"Invalid values found in x_column, y1_column, or y2_column. Rows with NaN/NaT will be dropped.")
            df_cleaned = df.dropna(subset=[request.x_column, request.y1_column, request.y2_column])  # 删除包含 NaN/NaT 的行
            x = df_cleaned[request.x_column]
            y1 = pd.to_numeric(df_cleaned[request.y1_column])
            y2 = pd.to_numeric(df_cleaned[request.y2_column])
        
        # 设置图表尺寸
        plt.figure(figsize=(request.width, request.height))
        
        # 绘制第一条折线
        plt.plot(
            x, y1,
            color=request.color1,
            linestyle=request.line_style1.value,
            marker=request.marker_style1.value if request.marker_style1 else None,
            label=request.y1_label
        )
        
        # 绘制第二条折线
        plt.plot(
            x, y2,
            color=request.color2,
            linestyle=request.line_style2.value,
            marker=request.marker_style2.value if request.marker_style2 else None,
            label=request.y2_label
        )
        
        # 设置标题和标签
        plt.title(request.title)
        plt.xlabel(request.xlabel)
        plt.ylabel(request.y1_label)  # 默认使用第一个 Y 轴的标签
        
        # 根据 x_column 的数据类型调整 X 轴格式
        if pd.api.types.is_datetime64_any_dtype(x):  # 如果是时间格式
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))  # 设置日期格式
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
    
@app.post("/v1/sandbox/combinedyplot")
async def generate_combined_y_plot(request: CombinedYPlotRequest):
    try:
        # 打印当前工作目录和文件路径
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Reading CSV file: {request.file_path}")
        
        # 读取 CSV 文件
        df = pd.read_csv(request.file_path, sep=',', encoding='utf-8')
        logger.info(f"CSV columns: {df.columns}")
        
        # 检查指定的列是否存在
        if request.x_column not in df.columns or any(col not in df.columns for col in request.y_columns):
            logger.error(f"Specified columns not found: x_column={request.x_column}, y_columns={request.y_columns}")
            return {
                "code": -400,
                "message": "Specified columns not found in CSV file",
                "data": None
            }
        
        # 提取 X 列数据
        try:
            # 尝试将 x_column 转换为 datetime 类型
            x = pd.to_datetime(df[request.x_column], errors='coerce')
            if x.isnull().all():  # 如果全部转换失败，说明不是时间格式
                logger.info(f"x_column is not a datetime format, trying numeric...")
                x = pd.to_numeric(df[request.x_column], errors='coerce')  # 尝试转换为数值类型
                if x.isnull().all():  # 如果仍然全部转换失败，说明是字符串格式
                    logger.info(f"x_column is not numeric, treating as string/categorical.")
                    x = df[request.x_column].astype(str)  # 直接使用字符串格式
        except Exception as e:
            logger.error(f"Failed to convert x_column: {str(e)}")
            return {
                "code": -400,
                "message": f"Failed to convert x_column: {str(e)}",
                "data": None
            }
        
        # 提取 Y 列数据并计算组合值
        try:
            # 从 CSV 中提取需要的字段
            y_data = df[request.y_columns]
            
            # 提取常量
            P0 = request.constants.get("P0", 1.0)  # 默认值为 1.0
            d_tbm = request.constants.get("d_tbm", 1.0)  # 默认值为 1.0
            
            # 计算 Y 轴数据
            y = (4 * 1000 * P0) / (y_data[request.y_columns[0]] * y_data[request.y_columns[1]] * 60 * 3.14159 * d_tbm * d_tbm)
            
            # 检查是否有无效值
            if y.isnull().any():
                logger.warning(f"Invalid values found in y_data. Rows with NaN will be dropped.")
                df_cleaned = df.dropna(subset=request.y_columns)  # 删除包含 NaN 的行
                y_data = df_cleaned[request.y_columns]
                y = (4 * 1000 * P0) / (y_data[request.y_columns[0]] * y_data[request.y_columns[1]] * 60 * 3.14159 * d_tbm * d_tbm)
        except Exception as e:
            logger.error(f"Failed to calculate combined Y values: {str(e)}")
            return {
                "code": -400,
                "message": f"Failed to calculate combined Y values: {str(e)}",
                "data": None
            }
        
        # 设置图表尺寸
        plt.figure(figsize=(request.width, request.height))
        
        # 根据图表类型绘制
        if request.plot_type == PlotType.LINE:
            plt.plot(
                x, y,
                color=request.color,
                linestyle=request.line_style.value,
                marker=request.marker_style.value if request.marker_style else None,
                label="Combined Y"
            )
        elif request.plot_type == PlotType.SCATTER:
            plt.scatter(
                x, y,
                color=request.color,
                marker=request.marker_style.value if request.marker_style else "o",
                label="Combined Y"
            )
        elif request.plot_type == PlotType.BAR:
            plt.bar(
                x, y,
                color=request.color,
                label="Combined Y"
            )
        
        # 设置标题和标签
        plt.title(request.title)
        plt.xlabel(request.xlabel)
        plt.ylabel(request.ylabel)
        
        # 根据 x_column 的数据类型调整 X 轴格式
        if pd.api.types.is_datetime64_any_dtype(x):  # 如果是时间格式
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H'))  # 设置日期格式
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