# 数据库模块与CRUD服务API设计规范（V.2.1 基线）

## 背景与目标
- 在嵌入式场景下，以 SQLite 为主存，围绕记录（records）与生成子项（items）实现独立数据库模块与标准 CRUD 服务 API。
- 支持分片写入流程（A：创建主记录 → B：更新优化提示词 → C：逐张写子项 → D：收尾），保证幂等与可追踪。

## 架构概览
- 模块分层：
  - 数据访问层（DAL）：ConnectionManager、Repositories（RecordsRepo/ItemsRepo）、UnitOfWork
  - 服务层（db_service）：业务用例封装（create_record、update_prompts、add_item 等）、错误与日志
  - 控制器层（db_controller）：RESTful API 端点、参数校验与 OpenAPI 文档
- 运行模式：WAL、短事务、UPSERT 幂等；保留 NDJSON 作为审计源。

## 数据模型与ER
- records：id PK、job_id UNIQUE、user_id、session_id、created_at、base_prompt、category_prompt、refined_positive、refined_negative、aspect_ratio、quality、count、model_name、status、item_count、content_hash
- items：id PK、record_id FK→records(id) ON DELETE CASCADE、seed、temperature、top_p、relative_url、absolute_path、UNIQUE(record_id, relative_url, absolute_path)
- 索引：records(created_at)、records(category_prompt, model_name)、items(absolute_path)、items(relative_url)
- 可选 FTS5：fts_records(base_prompt, refined_positive, refined_negative)

## 分片写入流程（A/B/C/D）
- A 创建主记录：POST /api/records（status=submitted，UPSERT by job_id 幂等）
- B 更新优化提示词：PUT /api/records/{id} 或 /api/records/by-job/{job_id}（填 refined_*，status=generating）
- C 逐张写子项：POST /api/records/{id}/items（UNIQUE(record_id, relative_url, absolute_path) 去重；同事务累计 item_count）
- D 收尾：PUT /api/records/{id}（置 status=completed/failed，记录 item_count 与 count 差异）

## API 接口规范
- Records
  - POST /api/records：创建；请求含 job_id/user_id/session_id/created_at/base_prompt/category_prompt/aspect_ratio/quality/count/model_name
  - GET /api/records：分页与过滤（created_at、category、model、status、keyword（FTS））
  - GET /api/records/{id}：明细，含 items 汇总
  - PUT /api/records/{id}：部份更新（refined_*、status、quality 等）
  - DELETE /api/records/{id}：级联删除子项
- Items
  - POST /api/records/{id}/items：插入子项（seed、temperature、top_p、relative_url、absolute_path）
  - GET /api/records/{id}/items：分页查询
  - GET /api/records/{id}/items/{item_id}：子项明细
  - PUT /api/records/{id}/items/{item_id}：更新
  - DELETE /api/records/{id}/items/{item_id}：删除
- 参数校验：沿用现有比例/画质/范围/URL/路径校验；job_id/status/count 合法性检查。
- OpenAPI 文档：端点分 Tags（Records/Items），提供请求/响应示例与错误码说明。

## 事务、幂等与并发
- 事务：每次写操作在 UnitOfWork 中执行，失败 rollback；子项插入与计数更新同事务。
- 幂等：主表以 job_id UPSERT；子表以复合唯一键去重。
- 并发：启用 WAL；短事务避免锁竞争；批量插入可按 N 条事务提交。

## 错误处理与日志
- 错误码：422（校验失败）、404（未找到）、409（唯一冲突）、500（内部错误）
- 日志：操作类型、job_id/record_id、参数摘要、耗时、错误详情；记录摄取与校验指标。

## 数据字典
- 字段名称、类型、约束、含义（中文别名与英文字段对照），含枚举与取值范围（质量、状态）。

## 示例与测试
- 使用示例：分片流程 A→B→C→D 的请求与响应样例；查询/全文搜索示例。
- 测试用例：
  - 单元：仓储 CRUD、事务回滚、UPSERT 幂等、唯一冲突处理
  - 集成：端到端分片流程、多并发写、items 去重与计数一致性

## 实施计划
1) 完成本合并文档与评审
2) 代码实现：数据库模块 + 服务层 + 控制器端点 + OpenAPI 描述
3) 单元与集成测试，通过后上线灰度
4) 监控指标与日志校验，验证并发与幂等表现
