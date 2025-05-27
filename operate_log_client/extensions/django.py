"""
Django 集成模块。

提供简单的 Django 集成方式，只需在 settings 中配置即可使用。
"""
import json
import logging
import threading
from functools import wraps

from django.conf import settings
from django.http import HttpRequest

from ..logger import OperateLogger


class DjangoOperateLogger:
    """Django操作日志管理器类。"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """创建单例实例。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = super().__new__(cls)
                    except Exception as e:
                        logger = logging.getLogger(__name__)
                        logger.error(f"创建操作日志实例失败: {str(e)}")
                        return None
        return cls._instance

    def __init__(self):
        """初始化Django操作日志管理器。"""
        if not hasattr(self, "initialized"):
            try:
                if not hasattr(settings, "OPERATE_LOG"):
                    logger = logging.getLogger(__name__)
                    logger.warning("OPERATE_LOG 配置缺失，操作日志功能将被禁用。")
                    self.logger = None
                    self.initialized = True
                    return

                config = settings.OPERATE_LOG
                required_fields = ["kafka_servers", "topic"]
                missing_fields = [field for field in required_fields if field not in config]
                if missing_fields:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"OPERATE_LOG 配置缺少必要字段: {', '.join(missing_fields)}，操作日志功能将被禁用。")
                    self.logger = None
                    self.initialized = True
                    return

                self.logger = OperateLogger(
                    kafka_servers=config["kafka_servers"],
                    topic=config["topic"],
                    application=config.get("application", "django_app"),
                    environment=config.get("environment", "production"),
                    kafka_config=config.get("kafka_config", {}),
                )
                self.initialized = True
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"初始化操作日志失败: {str(e)}")
                self.logger = None
                self.initialized = True

    def log_operation(self, *args, **kwargs):
        """记录操作日志。"""
        if self.logger is None:
            return None
        try:
            return self.logger.log_operation(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"记录操作日志失败: {str(e)}")
            return None

    def log_batch(self, operations):
        """批量记录操作日志。"""
        if self.logger is None:
            return None
        try:
            return self.logger.log_batch(operations)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"批量记录操作日志失败: {str(e)}")
            return None

    def cleanup(self):
        """清理资源。"""
        if self.logger is None:
            return
        try:
            self.logger.cleanup()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"清理资源失败: {str(e)}")


# 创建全局单例实例
try:
    operate_logger = DjangoOperateLogger()
except Exception:
    operate_logger = None


def log_operation(
    operation_type=None, target=None, details=None, log_response=False, log_request=False
):
    """
    操作日志装饰器。

    参数:
        operation_type (str, optional): 操作类型
        target (str or callable, optional): 操作目标
        details (dict or callable, optional): 操作详情
        log_response (bool, optional): 是否记录返回值，默认为 False
        log_request (bool, optional): 是否记录请求参数，默认为 False

    使用示例:
    @log_operation(
        operation_type="CREATE_USER",
        target="user",
        log_response=True,
        log_request=True
    )
    def create_user(request, *args, **kwargs):
        # 函数实现
        pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            global operate_logger

            # 检查 operate_logger 是否可用
            if operate_logger is None or operate_logger.logger is None:
                # 尝试重新初始化
                try:
                    operate_logger = DjangoOperateLogger()
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"操作日志初始化失败: {str(e)}")
                    return func(request, *args, **kwargs)

            # 检查request参数
            if not isinstance(request, HttpRequest):
                # 如果是基于类的视图，尝试从args中获取request
                for arg in args:
                    if isinstance(arg, HttpRequest):
                        request = arg
                        break
                else:
                    # 如果找不到request，直接执行原函数
                    return func(request, *args, **kwargs)

            try:
                # 获取操作类型
                op_type = operation_type or f"{func.__name__.upper()}"

                # 获取操作目标
                op_target = target
                if callable(target):
                    op_target = target(request, *args, **kwargs)

                # 获取操作详情
                log_details = {}

                # 添加请求参数
                if log_request:
                    request_data = {}
                    # GET 参数
                    if request.GET:
                        request_data["get"] = dict(request.GET.items())
                    # POST 参数
                    if request.POST:
                        request_data["post"] = dict(request.POST.items())
                    # 请求体
                    if request.body:
                        try:
                            request_data["body"] = json.loads(request.body)
                        except json.JSONDecodeError:
                            request_data["body"] = str(request.body)
                    log_details["request"] = request_data

                # 添加自定义详情
                if details:
                    if callable(details):
                        custom_details = details(request, *args, **kwargs)
                    else:
                        custom_details = details
                    log_details.update(custom_details)

                # 执行原函数
                response = func(request, *args, **kwargs)

                # 添加返回值
                if log_response:
                    if hasattr(response, "content"):
                        try:
                            response_data = json.loads(response.content)
                            log_details["response"] = response_data
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            log_details["response"] = str(response.content)
                    else:
                        log_details["response"] = str(response)

                # 记录操作日志
                if operate_logger and operate_logger.logger:
                    operate_logger.log_operation(
                        operation_type=op_type,
                        operator=request.user.username if hasattr(request, "user") else "system",
                        target=op_target,
                        details=log_details,
                        user_id=getattr(request.user, "id", None)
                        if hasattr(request, "user")
                        else None,
                        subuser_id=getattr(request.user, "subuser_id", None)
                        if hasattr(request, "user")
                        else None,
                        request_id=request.META.get("HTTP_X_REQUEST_ID"),
                        source_ip=request.META.get("REMOTE_ADDR"),
                    )

                return response

            except Exception as e:
                # 记录错误并继续执行
                logger = logging.getLogger(__name__)
                logger.error(f"记录操作日志时发生错误: {str(e)}")
                return func(request, *args, **kwargs)

        return wrapper

    return decorator
