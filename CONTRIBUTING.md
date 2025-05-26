# 贡献指南

感谢您对 OperateLogClient 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 提交 Bug 报告
- 提出新功能建议
- 改进文档
- 提交代码修复
- 添加新功能

## 开发环境设置

1. Fork 本仓库
2. 克隆您的 Fork：
   ```bash
   git clone https://github.com/your-username/python-operate-log-client.git
   cd python-operate-log-client
   ```
3. 创建并激活虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   .\venv\Scripts\activate  # Windows
   ```
4. 安装开发依赖：
   ```bash
   pip install -r requirements-dev.txt
   ```
5. 安装 pre-commit 钩子：
   ```bash
   pre-commit install
   ```

## 代码规范

- 遵循 PEP 8 编码规范
- 使用 black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查
- 所有代码必须通过测试

## 提交 Pull Request

1. 创建新的分支：
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. 进行修改并提交：
   ```bash
   git add .
   git commit -m "描述你的修改"
   ```
3. 推送到您的 Fork：
   ```bash
   git push origin feature/your-feature-name
   ```
4. 创建 Pull Request

## 提交规范

提交信息应遵循以下格式：
```
类型: 简短描述

详细描述（可选）

相关 Issue（可选）
```

类型包括：
- feat: 新功能
- fix: 修复
- docs: 文档更新
- style: 代码格式（不影响代码运行的变动）
- refactor: 重构（既不是新增功能，也不是修改 bug 的代码变动）
- test: 增加测试
- chore: 构建过程或辅助工具的变动

## 测试

- 运行所有测试：
  ```bash
  pytest
  ```
- 运行带覆盖率报告的测试：
  ```bash
  pytest --cov=operate_log_client
  ```

## 文档

- 所有新功能必须包含文档
- 更新 README.md 中的相关部分
- 添加必要的示例代码

## 行为准则

- 尊重所有贡献者
- 接受建设性的批评
- 关注问题本身
- 保持专业和友善

## 问题反馈

如果您发现任何问题或有任何建议，请：

1. 检查是否已有相关 Issue
2. 如果没有，创建新的 Issue
3. 提供详细的问题描述和复现步骤

感谢您的贡献！
