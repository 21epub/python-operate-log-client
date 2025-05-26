"""
基本使用示例模块。

演示如何初始化和使用 OperateLogger。
"""
import os
import uuid

from operate_log_client import OperateLogger


def main():
    """
    基本使用示例模块。

    演示如何初始化和使用 OperateLogger。
    """
    # 阿里云SLS配置
    project = "operate-log-all-system"  # 项目名称
    logstore = "epub360"  # 日志库名称
    endpoint = "cn-hangzhou.log.aliyuncs.com"  # 根据实际地域配置
    access_key_id = os.getenv("SLS_ACCESS_KEY_ID")  # 从环境变量获取AccessKey
    access_key_secret = os.getenv("SLS_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        raise ValueError("请设置环境变量 SLS_ACCESS_KEY_ID 和 SLS_ACCESS_KEY_SECRET")

    # 使用上下文管理器（推荐方式）
    with OperateLogger(
        kafka_servers=[f"{project}.{endpoint}:10012"],
        topic=f"{logstore}.json",
        application="example_app",
        environment="development",
        kafka_config={
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "PLAIN",
            "sasl_plain_username": project,
            "sasl_plain_password": f"{access_key_id}#{access_key_secret}",
        },
    ) as logger:
        # 生成请求追踪ID
        request_id = str(uuid.uuid4())
        trace_context = {
            "trace_id": str(uuid.uuid4()),
            "parent_id": None,
            "span_id": str(uuid.uuid4()),
            "service": "user_service",
        }

        # 示例1：租户管理员创建新用户
        operation_id = logger.log_operation(
            operation_type="CREATE_TENANT_USER",
            operator="admin",
            target="user123",
            user_id="tenant_001",  # 租户ID
            subuser_id="user123",  # 租户下的用户ID
            details={
                "username": "john_doe",
                "email": "john@example.com",
                "role": "editor",
                "department": "marketing",
            },
            request_id=request_id,
            trace_context=trace_context,
        )
        print(f"Single operation logged with ID: {operation_id}, Request ID: {request_id}")

        # 示例2：租户管理员修改用户权限
        operation_id = logger.log_operation(
            operation_type="UPDATE_USER_PERMISSIONS",
            operator="admin",
            target="user123",
            user_id="tenant_001",  # 租户ID
            subuser_id="user123",  # 租户下的用户ID
            details={
                "old_permissions": ["read"],
                "new_permissions": ["read", "write", "publish"],
                "reason": "promoted to senior editor",
            },
            request_id=request_id,
            trace_context={**trace_context, "span_id": str(uuid.uuid4())},
        )

        # 示例3：批量操作用户
        operations = [
            {
                "operation_type": "UPDATE_USER_PROFILE",
                "operator": "admin",
                "target": "user123",
                "user_id": "tenant_001",  # 租户ID
                "subuser_id": "user123",  # 租户下的用户ID
                "details": {
                    "field": "phone",
                    "value": "1234567890",
                    "reason": "contact information update",
                },
                "request_id": request_id,
                "trace_context": {**trace_context, "span_id": str(uuid.uuid4())},
            },
            {
                "operation_type": "ASSIGN_USER_TO_TEAM",
                "operator": "admin",
                "target": "team_marketing",
                "user_id": "tenant_001",  # 租户ID
                "subuser_id": "user123",  # 租户下的用户ID
                "details": {
                    "team_id": "team_marketing",
                    "team_name": "Marketing Team",
                    "role": "team_member",
                },
                "request_id": request_id,
                "trace_context": {**trace_context, "span_id": str(uuid.uuid4())},
            },
        ]

        operation_ids = logger.log_batch(operations)
        print(f"Batch operations logged with IDs: {operation_ids}")


if __name__ == "__main__":
    main()
