## 版本策略
- 提交当前代码并创建发布标签：V.2.1（说明：嵌入系统数据库）
- 从标签派生开发分支：feature/sqlite-crud（基于 V.2.1），在该分支完成数据库模块与 CRUD API
- 合并至 main 后打 V.2.1.1（或 V.2.2）作为交付版本

## 合并文档（一次交付）
- 数据库模块与 CRUD 服务 API 设计规范（架构/ER/接口/事务与幂等/错误码/数据字典/示例与测试）
- 作为唯一技术文档提交到仓库 docs/ 下，并在 README 增加入口链接

## 开发步骤
1) 文档落地与评审（合并文档）
   - 明确表结构、索引、约束、状态机
   - API 端点、请求/响应模型、错误码与示例
   - 分片写入流程 A/B/C/D 的交互序列图
2) 数据库模块实现（backend/db）
   - ConnectionManager（SQLite+WAL）、Repositories（Records/Items）、UnitOfWork
   - DTO/校验（沿用现有 validators）与错误映射
3) 服务层（backend/services/db_service）
   - 用例：create_record、update_prompts、add_item、delete_record、query_records
   - 幂等与去重：UPSERT by job_id；子项 UNIQUE(record_id, relative_url, absolute_path)
4) 控制器层（backend/controllers/db_controller）
   - RESTful 端点：POST/GET/PUT/DELETE（Records/Items）
   - OpenAPI 文档（Tags/示例/错误码）
5) 测试
   - 单元：仓储 CRUD、事务回滚、幂等与唯一冲突
   - 集成：端到端分片流程、多并发写、items 计数一致性
6) 联调与灰度
   - 与现有生成流程按 A/B/C/D 接口联动（保持 NDJSON 审计源不变）
   - 指标与日志校验（错误率、写入耗时、锁等待）

## 验收与发布
- 完成测试后合并至 main，创建交付标签（V.2.1.1 或 V.2.2）
- 发布说明：新增嵌入式数据库模块与 CRUD API、分片写入支持、OpenAPI 文档与示例

如确认以上计划，我将按该流程推进：先提交与打标签（V.2.1），随后在 feature/sqlite-crud 分支完成文档→实现→测试→发布。