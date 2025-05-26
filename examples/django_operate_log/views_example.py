"""
Django 视图日志记录示例模块。

演示如何在视图中使用日志装饰器和直接调用日志。
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from operate_log_client.extensions.django import log_operation, operate_logger


# 方式1：使用装饰器
class UserView(View):
    """用户视图类。"""

    @method_decorator(
        log_operation(
            operation_type="CREATE_USER",
            target="user",
            log_response=True,  # 记录返回值
            log_request=True,  # 记录请求参数
        )
    )
    def post(self, request, *args, **kwargs):
        """处理用户创建请求。"""
        # 创建用户的逻辑
        return JsonResponse(
            {"status": "success", "user_id": "user_123", "message": "User created successfully"}
        )

    @method_decorator(
        log_operation(
            operation_type="UPDATE_USER",
            target=lambda request, *args, **kwargs: f"user_{kwargs.get('user_id')}",
            log_request=True,  # 记录请求参数
        )
    )
    def put(self, request, *args, **kwargs):
        """处理用户更新请求。"""
        # 更新用户的逻辑
        return JsonResponse({"status": "success", "message": "User updated successfully"})


# 方式2：直接使用logger
class TeamView(View):
    """团队视图类。"""

    def post(self, request, *args, **kwargs):
        """处理团队创建请求。"""
        # 创建团队的逻辑
        team_id = "team_123"  # 假设这是新创建的团队ID
        response = JsonResponse(
            {"status": "success", "team_id": team_id, "message": "Team created successfully"}
        )

        # 记录操作日志
        operate_logger.log_operation(
            operation_type="CREATE_TEAM",
            operator=request.user.username,
            target=f"team_{team_id}",
            details={
                "team_name": request.POST.get("name"),
                "members": request.POST.getlist("members"),
                "request": {  # 手动添加请求参数
                    "post": dict(request.POST.items()),
                    "headers": {
                        k: v
                        for k, v in request.META.items()
                        if k.startswith("HTTP_") or k in ("CONTENT_TYPE", "CONTENT_LENGTH")
                    },
                },
                "response": {  # 手动添加返回值
                    "status": "success",
                    "team_id": team_id,
                    "message": "Team created successfully",
                },
            },
            user_id=request.user.tenant_id,
            subuser_id=request.user.id,
        )

        return response

    def delete(self, request, *args, **kwargs):
        """处理团队删除请求。"""
        team_id = kwargs.get("team_id")
        response = JsonResponse({"status": "success", "message": "Team deleted successfully"})

        # 批量记录操作日志
        operations = [
            {
                "operation_type": "DELETE_TEAM",
                "operator": request.user.username,
                "target": f"team_{team_id}",
                "details": {
                    "team_id": team_id,
                    "request": {  # 手动添加请求参数
                        "get": dict(request.GET.items()),
                        "headers": {
                            k: v
                            for k, v in request.META.items()
                            if k.startswith("HTTP_") or k in ("CONTENT_TYPE", "CONTENT_LENGTH")
                        },
                    },
                    "response": {  # 手动添加返回值
                        "status": "success",
                        "message": "Team deleted successfully",
                    },
                },
                "user_id": request.user.tenant_id,
                "subuser_id": request.user.id,
            },
            {
                "operation_type": "REMOVE_TEAM_MEMBERS",
                "operator": request.user.username,
                "target": f"team_{team_id}",
                "details": {
                    "team_id": team_id,
                    "member_count": 10,  # 假设有10个成员
                    "request": {  # 手动添加请求参数
                        "get": dict(request.GET.items()),
                        "headers": {
                            k: v
                            for k, v in request.META.items()
                            if k.startswith("HTTP_") or k in ("CONTENT_TYPE", "CONTENT_LENGTH")
                        },
                    },
                    "response": {  # 手动添加返回值
                        "status": "success",
                        "message": "Team members removed successfully",
                    },
                },
                "user_id": request.user.tenant_id,
                "subuser_id": request.user.id,
            },
        ]

        operate_logger.log_batch(operations)
        return response


# 装饰整个类的示例
@method_decorator(
    log_operation(
        operation_type="HEALTH_CHECK",
        target="system",
        details=lambda request, *args, **kwargs: {"status": "healthy"},
        log_request=True,  # 记录请求参数
        log_response=True,  # 记录返回值
    ),
    name="get",
)
class HealthCheckView(View):
    """健康检查视图类。"""

    def get(self, request, *args, **kwargs):
        """处理健康检查请求。"""
        return JsonResponse(
            {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",
                "services": ["api", "database", "cache"],
            }
        )
