import asyncio
import sys
import io
import tempfile
import os
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any
from concurrent.futures import ProcessPoolExecutor

def _run_python_code_in_process(code: str) -> Dict[str, Any]:
    """在进程中执行Python代码的函数"""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    
    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            global_namespace = {}
            exec(code, global_namespace)
            
        return {
            "success": True,
            "output": stdout_buffer.getvalue(),
            "error": stderr_buffer.getvalue() or None
        }
    except Exception as e:
        return {
            "success": False,
            "output": stdout_buffer.getvalue(),
            "error": str(e)
        }
    finally:
        stdout_buffer.close()
        stderr_buffer.close()

def _run_nodejs_code_in_process(code: str) -> Dict[str, Any]:
    """在进程中执行Node.js代码的函数"""
    try:
        # 创建临时文件来存储JavaScript代码
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        # 使用Node.js执行代码
        process = subprocess.Popen(
            ['node', temp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        # 删除临时文件
        os.unlink(temp_file_path)
        
        if process.returncode == 0:
            return {
                "success": True,
                "output": stdout,
                "error": None
            }
        else:
            return {
                "success": False,
                "output": stdout,
                "error": stderr
            }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def check_nodejs_available():
    """检查Node.js是否可用"""
    try:
        subprocess.run(['node', '--version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

class CodeExecutor:
    def __init__(self, timeout: int = 30, max_workers: int = 10):
        self.timeout = timeout
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers)
        self.nodejs_available = check_nodejs_available()
    
    async def shutdown(self):
        """关闭进程池"""
        self.process_pool.shutdown(wait=True)

    async def execute(self, code: str, language: str = "python3") -> Dict[str, Any]:
        try:
            loop = asyncio.get_event_loop()
            
            if language == "python3":
                executor_func = _run_python_code_in_process
            elif language == "nodejs":
                if not self.nodejs_available:
                    return {
                        "success": False,
                        "output": "",
                        "error": "Node.js未安装或不可用"
                    }
                executor_func = _run_nodejs_code_in_process
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"不支持的语言: {language}"
                }
            
            future = loop.run_in_executor(
                self.process_pool,
                executor_func,
                code
            )
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return result

        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"代码执行超时 (>{self.timeout}秒)"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }