# 背景

当前系统已经提供用户列表分页查询功能，运营人员需要把筛选后的用户列表导出为Excel，用于线下核对和内部分析。

# 目标

在现有用户列表模块中增加Excel导出能力，保持筛选口径与现有列表查询一致。

# 输入

- 现有用户列表分页查询实现：`app/api/users.py` 的 `list_users` 接口函数，以及 `app/services/user_service.py` 的 `UserService.list_users`。
- 用户筛选条件：`app/api/users.py` 中的 `username`、`status` 查询参数；统一筛选入口为 `app/services/user_service.py` 的 `UserService.search_users`，仓储实现为 `app/repositories/user_repository.py` 的 `InMemoryUserRepository.search`。
- 当前用户数据模型：`app/models/user.py` 的 `User`、`UserStatus` 和 `UserListResponse`。
- 项目现有Excel导出工具：`app/utils/excel.py` 的 `build_excel` 和 `clean_text`。
- 项目规则文件与测试命令：根目录 `AGENTS.md`，全量测试命令为 `./scripts/test.sh`。

# 约束

- 不引入新的第三方依赖；
- 复用现有分页查询或筛选逻辑，不重新实现另一套查询；
- 最大导出数量为10000行；超过上限时拒绝导出，返回 HTTP 422 和明确错误信息；
- 不修改无关模块；
- 保持现有接口和测试兼容；
- 遵守项目规则文件中的代码规范与测试要求。

# 输出

- 新增用户列表Excel导出接口；
- Excel列为：用户ID、用户名、显示名称、邮箱、状态、创建时间；
- 中文列名；
- 对应的服务层实现；
- 单元测试或接口测试；
- 变更说明。

# 验收

- 空列表导出不报错；
- `display_name`为`null`时正常导出为空字符串；
- 中文列名正确；
- 筛选结果与用户列表查询口径一致；
- 超过10000行时拒绝导出，返回 HTTP 422 和明确错误信息；
- 附带对应自动化测试；
- 全量测试通过；
- 未引入新依赖；
- 未修改无关文件。

