"""
Django 配置示例模块。

演示如何在 Django 项目中配置操作日志。
"""

# 操作日志配置
OPERATE_LOG = {
    # 必填配置
    "kafka_servers": ["my-project-name.cn-hangzhou.log.aliyuncs.com:10012"],  # Kafka 服务器地址列表
    "topic": "my-logstore-name.json",  # Kafka 主题
    # 可选配置
    "application": "my_app",  # 应用名称，默认为 django_app
    "environment": "production",  # 环境名称，默认为 production
    # Kafka 配置（可选）
    "kafka_config": {
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": "my-project-name",  # 项目名称
        "sasl_plain_password": "${SLS_ACCESS_KEY_ID}#${SLS_ACCESS_KEY_SECRET}",  # 从环境变量获取
    },
}

# 注意：
# 1. 请确保设置了环境变量 SLS_ACCESS_KEY_ID 和 SLS_ACCESS_KEY_SECRET
# 2. 实际使用时，建议将敏感信息（如 AccessKey）存储在环境变量或安全的配置管理系统中
# 3. 可以根据实际需求修改 application 和 environment 的值
