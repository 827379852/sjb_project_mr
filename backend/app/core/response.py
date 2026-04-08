"""
标准 API 响应模型 - 所有接口统一返回格式
"""
from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应封装"""
    code: int = 0          # 0 = 成功，非 0 = 错误
    message: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: T = None, message: str = "ok") -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, message: str, code: int = 400, data: Any = None) -> "ApiResponse":
        return cls(code=code, message=message, data=data)


class PaginatedData(BaseModel, Generic[T]):
    """分页数据封装"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_more: bool

    @classmethod
    def build(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedData[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )