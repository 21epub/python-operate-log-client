# 操作日志客户端 (Operation Log Client)

这是一个用于记录操作日志的Python客户端库，支持将日志发送到阿里云SLS（日志服务）。特别适用于多租户系统的操作日志记录。

## 特性

- 简单易用的API接口
- 支持阿里云SLS日志服务
- 支持多租户场景
- 支持分布式追踪
- 灵活的日志格式配置
- 异步日志处理
- 内置重试机制

## 安装

### 从GitHub安装

```bash
# 使用pip直接安装
pip install git+https://github.com/21epub/python-operate-log-client.git

# 或者克隆后安装
git clone https://github.com/21epub/python-operate-log-client.git
cd python-operate-log-client
pip install -e .
```

### 开发环境设置

```bash
# 1. 创建并激活虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 2. 安装pre-commit
pip install pre-commit

# 3. 安装开发依赖
pip install -r requirements-dev.txt

# 4. 安装pre-commit钩子
pre-commit install
```

### 依赖要求

- Python >= 3.7
- kafka-python >= 2.0.2
- python-json-logger >= 2.0.7
- pydantic >= 2.0.0

## 开发指南

### 代码规范

项目使用以下工具确保代码质量：

- black: 代码格式化
- isort: import语句排序
- flake8: 代码风格检查
- pre-commit: 提交前检查

#### 本地代码检查

```bash
# 手动运行所有检查
pre-commit run --all-files

# 运行单个检查
pre-commit run black --all-files
pre-commit run isort --all-files
pre-commit run flake8 --all-files
```

#### 自动修复

```bash
# 格式化代码
black operate_log_client tests

# 排序imports
isort operate_log_client tests
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率报告的测试
pytest --cov=operate_log_client
```

## 快速开始

### 1. 配置环境变量

```bash
# 设置阿里云访问密钥
export SLS_ACCESS_KEY_ID="your-access-key-id"
export SLS_ACCESS_KEY_SECRET="your-access-key-secret"
```

### 2. 基本使用

```python
from operate_log_client import OperateLogger

# 初始化日志记录器
logger = OperateLogger(
    kafka_servers=['your-project.cn-hangzhou.log.aliyuncs.com:10012'],
    topic='your-logstore.json',
    application='your_app',
    environment='production'
)

# 记录操作日志
logger.log_operation(
    operation_type="CREATE_TENANT_USER",
    operator="admin",
    target="user123",
    user_id="tenant_001",     # 租户ID
    subuser_id="user123",     # 租户下的用户ID
    details={
        "username": "john_doe",
        "role": "editor"
    }
)
```

### 3. 多租户场景示例

```python
# 租户管理员创建新用户
logger.log_operation(
    operation_type="CREATE_TENANT_USER",
    operator="admin",
    target="user123",
    user_id="tenant_001",     # 租户ID
    subuser_id="user123",     # 租户下的用户ID
    details={
        "username": "john_doe",
        "email": "john@example.com",
        "role": "editor",
        "department": "marketing"
    }
)

# 租户管理员修改用户权限
logger.log_operation(
    operation_type="UPDATE_USER_PERMISSIONS",
    operator="admin",
    target="user123",
    user_id="tenant_001",     # 租户ID
    subuser_id="user123",     # 租户下的用户ID
    details={
        "old_permissions": ["read"],
        "new_permissions": ["read", "write", "publish"]
    }
)
```

### 4. 批量操作

```python
operations = [
    {
        "operation_type": "UPDATE_USER_PROFILE",
        "operator": "admin",
        "target": "user123",
        "user_id": "tenant_001",
        "subuser_id": "user123",
        "details": {"field": "phone", "value": "1234567890"}
    },
    {
        "operation_type": "ASSIGN_USER_TO_TEAM",
        "operator": "admin",
        "target": "team_marketing",
        "user_id": "tenant_001",
        "subuser_id": "user123",
        "details": {
            "team_id": "team_marketing",
            "role": "team_member"
        }
    }
]

operation_ids = logger.log_batch(operations)
```

### 5. Django集成示例

项目提供了Django集成的示例代码，位于 `examples/django_operate_log` 目录下：

1. 配置示例 (`settings_example.py`):
```python
OPERATE_LOG = {
    'kafka_servers': ['your-project.endpoint:port'],
    'topic': 'your-logstore.json',
    'application': 'your_django_app',
    'environment': 'production',
    'kafka_config': {
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'PLAIN',
        'sasl_plain_username': 'your-project',
        'sasl_plain_password': 'your-access-key-id#your-access-key-secret'
    }
}
```

2. 视图示例 (`views_example.py`):
```python
from django.views import View
from django.http import JsonResponse
from .logger import log_operation, operate_logger

class UserView(View):
    @log_operation(
        operation_type="CREATE_USER",
        target="user",
        details=lambda request, *args, **kwargs: {
            "username": request.POST.get("username"),
            "email": request.POST.get("email"),
            "role": request.POST.get("role")
        }
    )
    def post(self, request):
        # 创建用户的业务逻辑
        return JsonResponse({"status": "success"})

    @log_operation(
        operation_type="UPDATE_USER",
        target=lambda request, *args, **kwargs: f"user_{kwargs['user_id']}"
    )
    def put(self, request, user_id):
        # 更新用户的业务逻辑
        return JsonResponse({"status": "success"})
```

3. 日志记录器 (`logger.py`):
```python
from operate_log_client import OperateLogger
from django.conf import settings

operate_logger = OperateLogger(
    kafka_servers=settings.OPERATE_LOG['kafka_servers'],
    topic=settings.OPERATE_LOG['topic'],
    application=settings.OPERATE_LOG['application'],
    environment=settings.OPERATE_LOG['environment'],
    kafka_config=settings.OPERATE_LOG.get('kafka_config', {})
)
```

## 配置说明

### 初始化参数

```python
logger = OperateLogger(
    kafka_servers=['your-project.endpoint:port'],  # SLS Kafka服务地址
    topic='your-logstore.json',                   # 日志库名称（添加.json后缀支持JSON解析）
    application='your_app',                       # 应用名称
    environment='production',                     # 环境名称
    kafka_config={                                # Kafka额外配置
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'PLAIN',
        'sasl_plain_username': 'your-project',
        'sasl_plain_password': 'your-access-key-id#your-access-key-secret'
    }
)
```

### 日志字段说明

- `operation_id`: 操作ID（自动生成）
- `request_id`: 请求追踪ID（可选）
- `timestamp`: 操作时间（自动生成）
- `operation_type`: 操作类型
- `operator`: 操作人
- `user_id`: 租户ID
- `subuser_id`: 租户下的用户ID
- `target`: 操作对象
- `status`: 操作状态（默认"SUCCESS"）
- `details`: 操作详情
- `source_ip`: 来源IP（可选）
- `application`: 应用名称
- `environment`: 环境名称
- `trace_context`: 追踪上下文（可选）

## 最佳实践

1. **环境变量管理**
   - 使用环境变量管理敏感信息
   - 不同环境使用不同的配置

2. **错误处理**
   ```python
   try:
       logger.log_operation(...)
   except Exception as e:
       # 处理错误
       print(f"Failed to log operation: {e}")
   finally:
       logger.flush()
       logger.close()
   ```

3. **批量操作**
   - 使用`log_batch`进行批量操作
   - 注意控制批量大小

4. **资源清理**
   - 使用完毕后调用`close()`
   - 使用`with`语句自动管理资源

## 常见问题

1. **连接失败**
   - 检查AccessKey是否正确
   - 确认网络连接
   - 验证Project和Logstore是否存在

2. **日志格式问题**
   - 确保添加`.json`后缀
   - 检查details字段格式

3. **权限问题**
   - 确认AccessKey有足够权限
   - 检查Project和Logstore权限

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License
