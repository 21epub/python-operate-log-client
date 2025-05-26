"""
操作日志记录器模块。

提供日志记录、批量日志、Kafka集成等功能。
"""

import json
import logging
import socket
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError
from pythonjsonlogger import jsonlogger

from .models import OperationLog


class OperateLogger:
    """操作日志记录器类。"""

    def __init__(
        self,
        kafka_servers: List[str],
        topic: str,
        application: str = None,
        environment: str = None,
        kafka_config: Dict[str, Any] = None,
        auto_cleanup: bool = True,
    ):
        """
        初始化日志记录器。

        Args:
            kafka_servers: Kafka服务器地址列表。
            topic: Kafka主题。
            application: 应用名称。
            environment: 环境名称。
            kafka_config: Kafka配置。
            auto_cleanup: 是否自动清理资源（默认为True）。
        """
        self.kafka_servers = kafka_servers
        self.topic = topic
        self.application = application
        self.environment = environment
        self.kafka_config = kafka_config or {}
        self.auto_cleanup = auto_cleanup

        # 初始化Kafka生产者
        self.producer = None
        self._init_producer()

        # 初始化本地日志记录器
        self._init_logger()

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出。"""
        self.cleanup()

    def __del__(self):
        """析构函数。"""
        if self.auto_cleanup:
            self.cleanup()

    def _init_producer(self):
        """初始化Kafka生产者。"""
        # 配置Kafka生产者
        default_config = {
            "bootstrap_servers": self.kafka_servers,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
            "retries": 3,
            "acks": "all",
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "ssl_check_hostname": True,
        }

        # 合并配置
        merged_config = {**default_config, **self.kafka_config}

        # 处理SASL配置
        if "sasl_jaas_config" in self.kafka_config:
            import ssl

            merged_config.update(
                {
                    "ssl_context": ssl.create_default_context(),
                    "sasl_plain_username": self.kafka_config.get("sasl_plain_username"),
                    "sasl_plain_password": self.kafka_config.get("sasl_plain_password"),
                }
            )

        self.producer = KafkaProducer(**merged_config)

        self.hostname = socket.gethostname()

    def _init_logger(self):
        """初始化本地日志记录器。"""
        self.logger = logging.getLogger("operate_logger")
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter("%(timestamp)s %(level)s %(message)s %(operation_id)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_operation(
        self,
        operation_type: str,
        operator: str,
        target: str,
        details: Dict[str, Any] = None,
        status: str = "SUCCESS",
        source_ip: str = None,
        request_id: str = None,
        trace_context: Dict[str, Any] = None,
        user_id: str = None,
        subuser_id: str = None,
        **kwargs,
    ) -> str:
        """
        记录单个操作日志。

        Args:
            operation_type: 操作类型。
            operator: 操作人。
            target: 操作对象。
            details: 操作详情。
            status: 操作状态。
            source_ip: 来源IP。
            request_id: 请求追踪ID。
            trace_context: 追踪上下文信息。
            user_id: 被操作的用户ID。
            subuser_id: 被操作的子用户ID。
            **kwargs: 其他自定义字段。

        Returns:
            str: 操作ID。
        """
        operation_id = str(uuid.uuid4())

        log = OperationLog(
            operation_id=operation_id,
            request_id=request_id,
            timestamp=datetime.utcnow(),
            operation_type=operation_type,
            operator=operator,
            user_id=user_id,
            subuser_id=subuser_id,
            target=target,
            status=status,
            details=details or {},
            source_ip=source_ip,
            application=self.application,
            environment=self.environment,
            trace_context=trace_context or {},
            **kwargs,
        )

        # 发送到Kafka
        try:
            future = self.producer.send(self.topic, value=json.loads(log.json()))  # 转换为dict
            future.get(timeout=2)  # 等待发送完成
        except KafkaError as e:
            self.logger.error(
                "Failed to send log to Kafka", extra={"operation_id": operation_id, "error": str(e)}
            )

        # 本地日志记录
        self.logger.info(
            f"Operation logged: {operation_type}",
            extra={
                "operation_id": operation_id,
                "operator": operator,
                "target": target,
                "status": status,
            },
        )

        return operation_id

    def log_batch(self, operations: List[Dict[str, Any]]) -> List[str]:
        """
        批量记录操作日志。

        Args:
            operations: 操作日志列表。

        Returns:
            List[str]: 操作ID列表。
        """
        operation_ids = []
        for operation in operations:
            operation_id = self.log_operation(**operation)
            operation_ids.append(operation_id)
        return operation_ids

    def flush(self, timeout: Optional[float] = None):
        """
        强制刷新所有待发送的日志。

        Args:
            timeout: 超时时间（秒）。
        """
        self.producer.flush(timeout=timeout)

    def close(self):
        """关闭日志记录器。"""
        self.producer.close()

    def cleanup(self):
        """清理资源。"""
        try:
            self.flush()
            self.close()
        except Exception as e:
            print(f"清理资源时发生错误: {e}")
