import asyncio
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any
from concurrent.futures import ProcessPoolExecutor

def _run_code_in_process(code: str) -> Dict[str, Any]:
    """在进程中执行代码的函数"""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    
    try:
        # 同时重定向标准输出和标准错误
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            # 创建一个新的全局命名空间
            global_namespace = {}
            # 执行代码
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

class CodeExecutor:
    def __init__(self, timeout: int = 30, max_workers: int = 10):
        self.timeout = timeout
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers)
    
    async def shutdown(self):
        """关闭进程池"""
        self.process_pool.shutdown(wait=True)

    async def execute(self, code: str) -> Dict[str, Any]:
        try:
            # 使用进程池执行代码
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.process_pool,
                _run_code_in_process,
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