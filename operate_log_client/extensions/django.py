"""
Django 集成模块。

提供简单的 Django 集成方式，只需在 settings 中配置即可使用。
"""
import json
import logging
import sys
import threading
from functools import wraps

from django.conf import settings
from django.http import HttpRequest

from ..logger import OperateLogger


# 配置默认的控制台日志
def _setup_default_logging():
    """设置默认的控制台日志配置。"""
    # 配置根 logger
    root_logger = logging.getLogger("operate_log_client")

    # 清除已有的处理器，避免重复配置
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)

    # 创建格式器
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    # 添加处理器到logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.WARNING)

    # 设置不传播到父logger
    root_logger.propagate = False

    # 同时配置子logger
    django_logger = logging.getLogger("operate_log_client.django")
    django_logger.setLevel(logging.DEBUG)


# 初始化默认日志配置
_setup_default_logging()


def _log_to_console(message, level="INFO"):
    """强制输出日志到控制台。"""
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level} [operate_log_client.django] - {message}", flush=True)


def _sanitize_data(data, field_name=None):
    """清理数据，将不可序列化的对象转换为可序列化的格式。"""
    if data is None:
        return None

    # 处理文件上传对象 - 只保留引用信息
    if hasattr(data, "read") and hasattr(data, "name"):
        # 这是一个文件对象，只返回引用信息
        return {
            "file_ref": {
                "name": getattr(data, "name", "unknown"),
                "field": field_name,
                "type": "file_reference",
            }
        }

    # 处理字典
    if isinstance(data, dict):
        return {key: _sanitize_data(value, key) for key, value in data.items()}

    # 处理 QueryDict
    if hasattr(data, "dict"):
        return {key: _sanitize_data(value, key) for key, value in data.dict().items()}

    # 处理列表
    if isinstance(data, (list, tuple)):
        return [_sanitize_data(item, field_name) for item in data]

    # 处理其他可迭代对象（但不是字符串）
    if hasattr(data, "__iter__") and not isinstance(data, (str, bytes)):
        try:
            return [_sanitize_data(item, field_name) for item in data]
        except Exception:
            return str(data)

    # 对于其他类型，尝试转换为字符串
    try:
        # 检查是否可以 JSON 序列化
        import json

        json.dumps(data)
        return data
    except (TypeError, ValueError):
        return str(data)


def _get_func_name(func):
    """安全地获取函数名。"""
    # 尝试获取 __name__ 属性
    if hasattr(func, "__name__"):
        return func.__name__

    # 如果是 functools.partial 对象，尝试获取原函数名
    if hasattr(func, "func") and hasattr(func.func, "__name__"):
        return func.func.__name__

    # 如果是其他包装对象，尝试获取 __wrapped__ 属性
    if hasattr(func, "__wrapped__") and hasattr(func.__wrapped__, "__name__"):
        return func.__wrapped__.__name__

    # 最后的备选方案
    return str(func).split(" ")[1] if " " in str(func) else "unknown_function"


def _extract_request_data(request):
    """提取请求数据。"""
    request_data = {}

    try:
        # GET 参数
        if hasattr(request, "GET") and request.GET:
            request_data["get"] = _sanitize_data(dict(request.GET.items()))

        # POST 参数
        if hasattr(request, "POST") and request.POST:
            request_data["post"] = _sanitize_data(dict(request.POST.items()))

        # 请求体（注意：在某些情况下可能无法访问）
        if hasattr(request, "body") and request.body:
            try:
                request_data["body"] = json.loads(request.body)
            except json.JSONDecodeError:
                request_data["body"] = str(request.body)
            except Exception as e:
                _log_to_console(f"访问request.body时出错: {str(e)}", "DEBUG")

        # 添加请求方法和路径信息
        if hasattr(request, "method"):
            request_data["method"] = request.method

        if hasattr(request, "path"):
            request_data["path"] = request.path

        # 添加内容类型
        if hasattr(request, "content_type"):
            request_data["content_type"] = request.content_type

        # 处理文件上传信息
        if hasattr(request, "FILES") and request.FILES:
            files_info = {}
            for field_name, file_obj in request.FILES.items():
                if hasattr(file_obj, "multiple_chunks") and callable(file_obj.multiple_chunks):
                    files_info[field_name] = {
                        "name": getattr(file_obj, "name", "unknown"),
                        "size": getattr(file_obj, "size", 0),
                        "content_type": getattr(file_obj, "content_type", "unknown"),
                        "charset": getattr(file_obj, "charset", None),
                        "multiple_chunks": file_obj.multiple_chunks()
                        if hasattr(file_obj, "multiple_chunks")
                        else False,
                        "type": "uploaded_file",
                    }
                else:
                    files_info[field_name] = str(file_obj)
            if files_info:
                request_data["files"] = files_info

    except Exception as e:
        _log_to_console(f"提取请求数据时发生错误: {str(e)}", "ERROR")
        # 如果提取失败，至少返回基本信息
        request_data = {
            "error": f"Failed to extract request data: {str(e)}",
            "method": getattr(request, "method", "unknown"),
            "path": getattr(request, "path", "unknown"),
        }

    return request_data


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
                        _log_to_console(f"创建操作日志实例失败: {str(e)}", "ERROR")
                        return None
        return cls._instance

    def __init__(self):
        """初始化Django操作日志管理器。"""
        if not hasattr(self, "initialized"):
            try:
                if not hasattr(settings, "OPERATE_LOG"):
                    _log_to_console("OPERATE_LOG 配置缺失，操作日志功能将被禁用。", "WARNING")
                    self.logger = None
                    self.initialized = True
                    return

                config = settings.OPERATE_LOG
                required_fields = ["kafka_servers", "topic"]
                missing_fields = [field for field in required_fields if field not in config]
                if missing_fields:
                    _log_to_console(
                        f"OPERATE_LOG 配置缺少必要字段: {', '.join(missing_fields)}，操作日志功能将被禁用。", "WARNING"
                    )
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

                _log_to_console("Django操作日志记录器初始化成功", "INFO")

            except Exception as e:
                _log_to_console(f"初始化操作日志失败: {str(e)}", "ERROR")
                self.logger = None
                self.initialized = True

    def log_operation(self, *args, **kwargs):
        """记录操作日志。"""
        if self.logger is None:
            return None
        try:
            return self.logger.log_operation(*args, **kwargs)
        except Exception as e:
            _log_to_console(f"记录操作日志失败: {str(e)}", "ERROR")
            return None

    def log_batch(self, operations):
        """批量记录操作日志。"""
        if self.logger is None:
            return None
        try:
            return self.logger.log_batch(operations)
        except Exception as e:
            _log_to_console(f"批量记录操作日志失败: {str(e)}", "ERROR")
            return None

    def cleanup(self):
        """清理资源。"""
        if self.logger is None:
            return
        try:
            self.logger.cleanup()
        except Exception as e:
            _log_to_console(f"清理资源失败: {str(e)}", "ERROR")


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

            func_name = _get_func_name(func)
            _log_to_console(f"开始处理请求: {func_name}", "DEBUG")

            # 检查 operate_logger 是否可用
            if operate_logger is None or operate_logger.logger is None:
                # 尝试重新初始化
                try:
                    operate_logger = DjangoOperateLogger()
                except Exception as e:
                    _log_to_console(f"操作日志初始化失败: {str(e)}", "ERROR")
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
                    _log_to_console("未找到request对象，跳过日志记录", "WARNING")
                    return func(request, *args, **kwargs)

            try:
                # 获取操作类型
                op_type = operation_type or f"{func_name.upper()}"
                _log_to_console(f"操作类型: {op_type}", "DEBUG")

                # 获取操作目标
                op_target = target
                if callable(target):
                    op_target = target(request, *args, **kwargs)
                _log_to_console(f"操作目标: {op_target}", "DEBUG")

                # 获取操作详情
                log_details = {}

                # 添加请求参数
                if log_request:
                    log_details["request"] = _extract_request_data(request)
                    _log_to_console(f"记录请求数据: {len(str(log_details['request']))} 字符", "DEBUG")

                # 添加自定义详情
                if details:
                    if callable(details):
                        custom_details = details(request, *args, **kwargs)
                    else:
                        custom_details = details
                    if custom_details:
                        log_details.update(custom_details)

                # 执行原函数
                _log_to_console(f"执行原函数: {func_name}", "DEBUG")
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
                    _log_to_console(
                        f"记录响应数据: {len(str(log_details.get('response', '')))} 字符", "DEBUG"
                    )

                # 记录操作日志
                if operate_logger and operate_logger.logger:
                    _log_to_console("准备记录操作日志到Kafka", "DEBUG")
                    operate_logger.log_operation(
                        operation_type=op_type,
                        operator=request.user.username
                        if hasattr(request, "user") and hasattr(request.user, "username")
                        else "system",
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

                    # 添加操作成功的控制台日志
                    user_name = (
                        request.user.username
                        if hasattr(request, "user") and hasattr(request.user, "username")
                        else "system"
                    )
                    _log_to_console(
                        f"Django操作日志记录成功: {op_type} - {op_target} - 操作者: {user_name}", "INFO"
                    )
                else:
                    _log_to_console("operate_logger 不可用，跳过Kafka日志记录", "WARNING")

                return response

            except Exception as e:
                # 记录错误并继续执行
                _log_to_console(f"记录操作日志时发生错误: {str(e)}", "ERROR")
                import traceback

                _log_to_console(f"错误详情: {traceback.format_exc()}", "ERROR")
                return func(request, *args, **kwargs)

        return wrapper

    return decorator
