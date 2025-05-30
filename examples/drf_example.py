"""
Django REST Framework 操作日志使用示例。

展示如何在DRF项目中使用操作日志记录功能。
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from operate_log_client.extensions.drf import log_operation


class MaterialViewSet(viewsets.ModelViewSet):
    """材料管理ViewSet示例。"""

    @log_operation(operation_type="LIST_MATERIALS", target="material", log_request=True)
    def list(self, request, *args, **kwargs):
        """列出材料列表。"""
        # 原有的list逻辑
        return super().list(request, *args, **kwargs)

    @log_operation(
        operation_type="CREATE_MATERIAL", target="material", log_request=True, log_response=True
    )
    def create(self, request, *args, **kwargs):
        """创建新材料。"""
        # 原有的create逻辑
        return super().create(request, *args, **kwargs)

    @log_operation(
        operation_type="UPDATE_MATERIAL",
        target=lambda request, *args, **kwargs: f"material_{kwargs.get('pk')}",
        log_request=True,
        log_response=True,
    )
    def update(self, request, *args, **kwargs):
        """更新材料信息。"""
        # 原有的update逻辑
        return super().update(request, *args, **kwargs)

    @log_operation(
        operation_type="PARTIAL_UPDATE_MATERIAL",
        target=lambda request, *args, **kwargs: f"material_{kwargs.get('pk')}",
        log_request=True,
        log_response=True,
    )
    def partial_update(self, request, *args, **kwargs):
        """部分更新材料信息。"""
        # 原有的partial_update逻辑
        return super().partial_update(request, *args, **kwargs)

    @log_operation(
        operation_type="DELETE_MATERIAL",
        target=lambda request, *args, **kwargs: f"material_{kwargs.get('pk')}",
    )
    def destroy(self, request, *args, **kwargs):
        """删除材料。"""
        # 原有的destroy逻辑
        return super().destroy(request, *args, **kwargs)

    @log_operation(
        operation_type="APPROVE_MATERIAL",
        target=lambda request, *args, **kwargs: f"material_{kwargs.get('pk')}",
        details=lambda request, *args, **kwargs: {
            "action": "approve",
            "approver": request.user.username if hasattr(request, "user") else "system",
        },
        log_request=True,
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """审批材料。"""
        # 自定义审批逻辑
        material = self.get_object()
        material.status = "approved"
        material.save()

        return Response({"status": "success", "message": "材料审批成功"})


# 函数视图示例
@log_operation(
    operation_type="SEARCH_MATERIALS", target="material_search", log_request=True, log_response=True
)
def search_materials(request):
    """搜索材料的函数视图示例。"""
    # 搜索逻辑
    query = request.query_params.get("q", "")

    return Response({"query": query, "results": []})  # 实际的搜索结果


# 自定义详情提取示例
def extract_material_details(request, *args, **kwargs):
    """提取材料相关的详细信息。"""
    details = {}

    # 从kwargs中提取材料ID
    if "pk" in kwargs:
        details["material_id"] = kwargs["pk"]

    # 从请求数据中提取材料类型
    if hasattr(request, "data") and "material_type" in request.data:
        details["material_type"] = request.data["material_type"]

    # 添加操作时间戳
    from datetime import datetime

    details["operation_timestamp"] = datetime.now().isoformat()

    return details


class PersonalMaterialViewSet(viewsets.ModelViewSet):
    """个人材料ViewSet，使用自定义详情提取。"""

    @log_operation(target="personal_material", details=extract_material_details, log_request=True)
    def create(self, request, *args, **kwargs):
        """创建个人材料。"""
        return super().create(request, *args, **kwargs)

    @log_operation(
        target=lambda request, *args, **kwargs: f"personal_material_{kwargs.get('material_usage')}",
        details=extract_material_details,
        log_request=True,
    )
    def list(self, request, *args, **kwargs):
        """根据使用类型列出个人材料。"""
        # 根据material_usage过滤材料
        return super().list(request, *args, **kwargs)
