"""
异常定义与全局异常处理器
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用级异常基类"""
    def __init__(self, message: str, code: int = 400, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} '{id}' 不存在", code=404, status_code=404)


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code=422, status_code=422)


class AgentBackendError(AppException):
    """Agent 后端执行异常"""
    def __init__(self, message: str):
        super().__init__(f"Agent 后端错误: {message}", code=500, status_code=500)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )