"""Django 日志配置示例。"""
# 操作日志配置
OPERATE_LOG = {
    "kafka_servers": ["your-project.cn-hangzhou.log.aliyuncs.com:10012"],
    "topic": "your-logstore.json",
    "application": "your_django_app",
    "environment": "production",  # 或 'development', 'staging' 等
    "kafka_config": {
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": "your-project",
        "sasl_plain_password": "your-access-key-id#your-access-key-secret",
    },
}
