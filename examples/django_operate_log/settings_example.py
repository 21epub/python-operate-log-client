"""
Django 配置示例模块。

演示如何在 Django 项目中配置操作日志。
"""

# 操作日志配置
OPERATE_LOG = {
    # 必填配置
    "kafka_servers": ["localhost:9092"],  # Kafka 服务器地址列表
    "topic": "operate_log",  # Kafka 主题
    # 可选配置
    "application": "my_app",  # 应用名称，默认为 django_app
    "environment": "production",  # 环境名称，默认为 production
    # Kafka 配置（可选）
    "kafka_config": {
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": "your_username",
        "sasl_plain_password": "your_password",
    },
}
