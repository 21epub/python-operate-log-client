"""
操作日志数据模型模块。

定义操作日志的数据结构和序列化配置。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OperationLog(BaseModel):
    """
    操作日志数据模型。

    包含操作日志的结构和序列化配置。
    """

    operation_id: str = Field(..., description="操作ID。")
    request_id: Optional[str] = Field(None, description="请求追踪ID，用于分布式追踪。")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="操作时间。")
    operation_type: str = Field(..., description="操作类型。")
    operator: str = Field(..., description="操作人。")
    user_id: Optional[str] = Field(None, description="租户ID，操作的租户。")
    subuser_id: Optional[str] = Field(None, description="用户ID，租户下的操作用户。")
    target: str = Field(..., description="操作对象。")
    status: str = Field(default="SUCCESS", description="操作状态。")
    details: Dict[str, Any] = Field(default_factory=dict, description="操作详情。")
    source_ip: Optional[str] = Field(None, description="来源IP。")
    application: Optional[str] = Field(None, description="应用名称。")
    environment: Optional[str] = Field(None, description="环境。")
    trace_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="追踪上下文，可包含parent_id, trace_id等OpenTelemetry/OpenTracing相关信息。",
    )

    class Config:
        """配置类。"""

        json_encoders = {datetime: lambda v: v.isoformat()}
