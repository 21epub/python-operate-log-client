"""
Django 集成模块。

提供简单的 Django 集成方式，只需在 settings 中配置即可使用。
"""

import threading
from functools import wraps

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .logger import OperateLogger


class DjangoOperateLogger:
    """Django操作日志管理器类。"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """创建单例实例。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化Django操作日志管理器。"""
        if not hasattr(self, "initialized"):
            if not hasattr(settings, "OPERATE_LOG"):
                raise ImproperlyConfigured("OPERATE_LOG 配置缺失。请在 settings.py 中添加 OPERATE_LOG 配置。")

            config = settings.OPERATE_LOG
            required_fields = ["kafka_servers", "topic"]
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                raise ImproperlyConfigured(f"OPERATE_LOG 配置缺少必要字段: {', '.join(missing_fields)}")

            self.logger = OperateLogger(
                kafka_servers=config["kafka_servers"],
                topic=config["topic"],
                application=config.get("application", "django_app"),
                environment=config.get("environment", "production"),
                kafka_config=config.get("kafka_config", {}),
            )
            self.initialized = True

    def log_operation(self, *args, **kwargs):
        """记录操作日志。"""
        return self.logger.log_operation(*args, **kwargs)

    def log_batch(self, operations):
        """批量记录操作日志。"""
        return self.logger.log_batch(operations)

    def cleanup(self):
        """清理资源。"""
        self.logger.cleanup()


# 创建全局单例实例
operate_logger = DjangoOperateLogger()


def log_operation(operation_type=None, target=None, details=None):
    """
    操作日志装饰器。

    使用示例:
    @log_operation(operation_type="CREATE_USER", target="user")
    def create_user(request, *args, **kwargs):
        # 函数实现
        pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 获取操作类型
            op_type = operation_type or f"{func.__name__.upper()}"

            # 获取操作目标
            op_target = target
            if callable(target):
                op_target = target(request, *args, **kwargs)

            # 获取操作详情
            op_details = details
            if callable(details):
                op_details = details(request, *args, **kwargs)

            # 记录操作日志
            operate_logger.log_operation(
                operation_type=op_type,
                operator=request.user.username if hasattr(request, "user") else "system",
                target=op_target,
                details=op_details,
                user_id=getattr(request.user, "tenant_id", None),
                subuser_id=getattr(request.user, "id", None),
                request_id=request.META.get("HTTP_X_REQUEST_ID"),
                source_ip=request.META.get("REMOTE_ADDR"),
            )

            return func(request, *args, **kwargs)

        return wrapper

    return decorator
