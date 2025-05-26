"""
Django 视图日志记录示例模块。

演示如何在视图中使用日志装饰器和直接调用日志。
"""
from django.http import JsonResponse
from django.views import View

from operate_log_client import log_operation, operate_logger


# 方式1：使用装饰器
class UserView(View):
    """用户视图类。"""

    @log_operation(
        operation_type="CREATE_USER",
        target=lambda request, *args, **kwargs: f"user_{request.POST.get('username')}",
        details=lambda request, *args, **kwargs: {
            "username": request.POST.get("username"),
            "email": request.POST.get("email"),
            "role": request.POST.get("role"),
        },
    )
    def post(self, request, *args, **kwargs):
        """处理用户创建请求。"""
        # 创建用户的逻辑
        return JsonResponse({"status": "success"})

    @log_operation(
        operation_type="UPDATE_USER",
        target=lambda request, *args, **kwargs: f"user_{kwargs.get('user_id')}",
    )
    def put(self, request, *args, **kwargs):
        """处理用户更新请求。"""
        # 更新用户的逻辑
        return JsonResponse({"status": "success"})


# 方式2：直接使用logger
class TeamView(View):
    """团队视图类。"""

    def post(self, request, *args, **kwargs):
        """处理团队创建请求。"""
        # 创建团队的逻辑
        team_id = "team_123"  # 假设这是新创建的团队ID

        # 记录操作日志
        operate_logger.log_operation(
            operation_type="CREATE_TEAM",
            operator=request.user.username,
            target=f"team_{team_id}",
            details={
                "team_name": request.POST.get("name"),
                "members": request.POST.getlist("members"),
            },
            user_id=request.user.tenant_id,
            subuser_id=request.user.id,
        )

        return JsonResponse({"status": "success"})

    def delete(self, request, *args, **kwargs):
        """处理团队删除请求。"""
        team_id = kwargs.get("team_id")

        # 批量记录操作日志
        operations = [
            {
                "operation_type": "DELETE_TEAM",
                "operator": request.user.username,
                "target": f"team_{team_id}",
                "details": {"team_id": team_id},
                "user_id": request.user.tenant_id,
                "subuser_id": request.user.id,
            },
            {
                "operation_type": "REMOVE_TEAM_MEMBERS",
                "operator": request.user.username,
                "target": f"team_{team_id}",
                "details": {"team_id": team_id, "member_count": 10},  # 假设有10个成员
                "user_id": request.user.tenant_id,
                "subuser_id": request.user.id,
            },
        ]

        operate_logger.log_batch(operations)
        return JsonResponse({"status": "success"})
