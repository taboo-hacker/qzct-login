# 贡献指南

感谢你考虑为 QZCT 校园登录助手做出贡献！

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 在 [Issues](https://github.com/taboo-hacker/qzct-login/issues) 中搜索是否已有相同问题
2. 如果没有，创建新 Issue，包含：
   - 清晰的标题
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（Python 版本、操作系统等）

### 提出新功能

1. 在 Issues 中描述你的想法
2. 等待维护者反馈
3. 获得批准后开始实现

### 提交代码

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 编写代码和测试
4. 确保通过所有检查：
   ```bash
   black . && isort .
   ruff check .
   mypy .
   pytest tests/ -v
   ```
5. 提交代码：`git commit -m "feat: add amazing feature"`
6. 推送分支：`git push origin feature/amazing-feature`
7. 创建 Pull Request

## 代码规范

- 遵循 PEP 8 风格指南
- 使用 Black 格式化代码
- 为函数添加类型注解
- 为公共 API 编写文档字符串
- 为新功能编写测试

## 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 关注对社区最有利的事情

## 许可证

通过贡献代码，你同意你的代码将在 CC BY-NC-SA 4.0 许可证下发布。
