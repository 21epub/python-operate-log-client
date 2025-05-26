"""
操作日志客户端包。

提供操作日志记录、批量日志、Kafka集成等功能。
"""

from .logger import OperateLogger
from .models import OperationLog

# Django 集成
try:
    from .extensions.django import log_operation, operate_logger
except ImportError:
    operate_logger = None
    log_operation = None

__version__ = "0.1.0"
__all__ = ["OperateLogger", "OperationLog", "operate_logger", "log_operation"]
