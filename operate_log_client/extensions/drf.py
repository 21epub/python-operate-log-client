"""
Django REST Framework 集成模块。

提供专门为 DRF 设计的操作日志记录功能。
"""
import json
import logging
import sys
import threading
from functools import wraps

from django.conf import settings
from django.http import HttpRequest

from ..logger import OperateLogger

try:
    from rest_framework.request import Request as DRFRequest
    from rest_framework.response import Response as DRFResponse

    DRF_AVAILABLE = True
except ImportError:
    DRFRequest = None
    DRFResponse = None
    DRF_AVAILABLE = False


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
    drf_logger = logging.getLogger("operate_log_client.drf")
    drf_logger.setLevel(logging.DEBUG)


# 初始化默认日志配置
_setup_default_logging()


def _log_to_console(message, level="INFO"):
    """强制输出日志到控制台。"""
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level} [operate_log_client.drf] - {message}", flush=True)


class DRFOperateLogger:
    """DRF操作日志管理器类。"""

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
        """初始化DRF操作日志管理器。"""
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
                    application=config.get("application", "drf_app"),
                    environment=config.get("environment", "production"),
                    kafka_config=config.get("kafka_config", {}),
                )
                self.initialized = True

                _log_to_console("DRF操作日志记录器初始化成功", "INFO")

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
    operate_logger = DRFOperateLogger()
except Exception:
    operate_logger = None


def _extract_request_data(request):
    """提取请求数据。"""
    request_data = {}

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

    try:
        # GET 参数 - 优先使用 DRF 的 query_params
        if hasattr(request, "query_params") and request.query_params:
            request_data["query_params"] = _sanitize_data(dict(request.query_params.items()))
        elif hasattr(request, "GET") and request.GET:
            request_data["get"] = _sanitize_data(dict(request.GET.items()))

        # POST/PUT/PATCH 数据 - 优先使用 DRF 的 data
        if hasattr(request, "data") and request.data is not None:
            try:
                # 清理数据，确保可序列化
                sanitized_data = _sanitize_data(request.data)
                request_data["data"] = sanitized_data
            except Exception as e:
                _log_to_console(f"提取 request.data 时出错: {str(e)}", "DEBUG")
                request_data["data"] = {"error": f"Failed to extract data: {str(e)}"}
        elif hasattr(request, "POST") and request.POST:
            # 如果没有 DRF 的 data，尝试使用 Django 的 POST
            request_data["post"] = _sanitize_data(dict(request.POST.items()))
        # 添加请求方法和路径信息
        if hasattr(request, "method"):
            request_data["method"] = request.method

        if hasattr(request, "path"):
            request_data["path"] = request.path
        elif hasattr(request, "_request") and hasattr(request._request, "path"):
            request_data["path"] = request._request.path

        # 添加内容类型
        if hasattr(request, "content_type"):
            request_data["content_type"] = request.content_type
        elif hasattr(request, "_request") and hasattr(request._request, "content_type"):
            request_data["content_type"] = request._request.content_type

        # 注意：避免访问 request.body，因为在 DRF 中可能已经被读取过了
        # 如果确实需要原始请求体，应该在 DRF 处理之前获取

    except Exception as e:
        _log_to_console(f"提取请求数据时发生错误: {str(e)}", "ERROR")
        # 如果提取失败，至少返回基本信息
        request_data = {
            "error": f"Failed to extract request data: {str(e)}",
            "method": getattr(request, "method", "unknown"),
            "path": getattr(
                request, "path", getattr(request, "_request", {}).get("path", "unknown")
            ),
        }

    return request_data


def _extract_response_data(response):
    """提取响应数据。"""
    if isinstance(response, DRFResponse):
        try:
            return response.data
        except Exception:
            return str(response.data)
    elif hasattr(response, "content"):
        try:
            return json.loads(response.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return str(response.content)
    else:
        return str(response)


def _get_operation_type_from_method(request, func_name):
    """根据HTTP方法和函数名推断操作类型。"""
    if hasattr(request, "method"):
        method = request.method.upper()

        # 常见的RESTful操作映射
        method_mapping = {
            "GET": "READ",
            "POST": "CREATE",
            "PUT": "UPDATE",
            "PATCH": "PARTIAL_UPDATE",
            "DELETE": "DELETE",
        }

        base_type = method_mapping.get(method, method)
        return f"{base_type}_{func_name.upper()}"

    return func_name.upper()


def _get_user_info(request):
    """获取用户信息。"""
    user_info = {
        "operator": "anonymous",
        "user_id": None,
        "subuser_id": None,
    }

    if hasattr(request, "user") and request.user:
        if hasattr(request.user, "is_authenticated") and request.user.is_authenticated:
            user_info["operator"] = getattr(request.user, "username", str(request.user))

            # 确保 user_id 是字符串类型
            user_id = getattr(request.user, "id", None)
            if user_id is not None:
                user_info["user_id"] = str(user_id)

            # 确保 subuser_id 是字符串类型
            subuser_id = getattr(request.user, "subuser_id", None)
            if subuser_id is not None:
                user_info["subuser_id"] = str(subuser_id)
        else:
            user_info["operator"] = "anonymous"

    return user_info


def _get_request_meta(request):
    """获取请求元信息。"""
    meta = {}

    # 尝试从DRF Request中获取
    if hasattr(request, "_request"):
        django_request = request._request
    elif hasattr(request, "META"):
        django_request = request
    else:
        return meta

    if hasattr(django_request, "META"):
        meta["request_id"] = django_request.META.get("HTTP_X_REQUEST_ID")
        meta["source_ip"] = django_request.META.get("REMOTE_ADDR")
        meta["user_agent"] = django_request.META.get("HTTP_USER_AGENT")
        meta["content_type"] = django_request.META.get("CONTENT_TYPE")

    return meta


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


def log_operation(
    operation_type=None, target=None, details=None, log_response=False, log_request=False
):
    """
    DRF操作日志装饰器。

    参数:
        operation_type (str, optional): 操作类型，如果不提供会根据HTTP方法自动推断
        target (str or callable, optional): 操作目标
        details (dict or callable, optional): 操作详情
        log_response (bool, optional): 是否记录响应数据，默认为 False
        log_request (bool, optional): 是否记录请求数据，默认为 False

    使用示例:
    @log_operation(
        operation_type="CREATE_USER",
        target="user",
        log_response=True,
        log_request=True
    )
    def create(self, request, *args, **kwargs):
        # ViewSet方法实现
        pass
    """

    if not DRF_AVAILABLE:

        def no_op_decorator(func):
            _log_to_console("Django REST Framework 未安装，日志装饰器已禁用", "WARNING")
            return func

        return no_op_decorator

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global operate_logger

            func_name = _get_func_name(func)
            _log_to_console(f"开始处理请求: {func_name}", "DEBUG")

            # 查找request对象
            request = None

            # 第一个参数通常是self（ViewSet实例），第二个是request
            if len(args) >= 2 and isinstance(args[1], (DRFRequest, HttpRequest)):
                request = args[1]
                _log_to_console(f"找到request对象在args[1]: {type(request)}", "DEBUG")
            # 或者第一个参数就是request（函数视图）
            elif len(args) >= 1 and isinstance(args[0], (DRFRequest, HttpRequest)):
                request = args[0]
                _log_to_console(f"找到request对象在args[0]: {type(request)}", "DEBUG")

            if request is None:
                _log_to_console("未找到request对象，跳过日志记录", "WARNING")
                return func(*args, **kwargs)

            # 检查 operate_logger 是否可用
            if operate_logger is None or operate_logger.logger is None:
                try:
                    operate_logger = DRFOperateLogger()
                except Exception as e:
                    _log_to_console(f"操作日志初始化失败: {str(e)}", "ERROR")
                    return func(*args, **kwargs)

            try:
                # 获取操作类型
                op_type = operation_type or _get_operation_type_from_method(request, func_name)
                _log_to_console(f"操作类型: {op_type}", "DEBUG")

                # 获取操作目标
                op_target = target
                if callable(target):
                    op_target = target(request, *args, **kwargs)
                _log_to_console(f"操作目标: {op_target}", "DEBUG")

                # 获取操作详情
                log_details = {}

                # 添加请求数据
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
                response = func(*args, **kwargs)

                # 添加响应数据
                if log_response:
                    log_details["response"] = _extract_response_data(response)
                    _log_to_console(f"记录响应数据: {len(str(log_details['response']))} 字符", "DEBUG")

                # 获取用户信息
                user_info = _get_user_info(request)

                # 获取请求元信息
                request_meta = _get_request_meta(request)

                # 记录操作日志
                if operate_logger and operate_logger.logger:
                    _log_to_console("准备记录操作日志到Kafka", "DEBUG")
                    operate_logger.log_operation(
                        operation_type=op_type,
                        operator=user_info["operator"],
                        target=op_target,
                        details=log_details,
                        user_id=user_info["user_id"],
                        subuser_id=user_info["subuser_id"],
                        request_id=request_meta.get("request_id"),
                        source_ip=request_meta.get("source_ip"),
                    )

                    # 添加操作成功的控制台日志
                    _log_to_console(
                        f"DRF操作日志记录成功: {op_type} - {op_target} - 操作者: {user_info['operator']}",
                        "INFO",
                    )
                else:
                    _log_to_console("operate_logger 不可用，跳过Kafka日志记录", "WARNING")

                return response

            except Exception as e:
                # 记录错误并继续执行
                _log_to_console(f"记录操作日志时发生错误: {str(e)}", "ERROR")
                import traceback

                _log_to_console(f"错误详情: {traceback.format_exc()}", "ERROR")
                return func(*args, **kwargs)

        return wrapper

    return decorator
