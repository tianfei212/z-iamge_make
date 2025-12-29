# 配置说明与模式切换

## operation_mode
- 取值：database 或 config_file
- 含义：决定统一运行时配置从数据库或配置文件读取
- 回退：非法值或数据库异常时回退为 config_file

## 配置结构
- models_list：数组，字段 id、name、provider、model_name、description、enabled
- categories：数组，分类名称列表
- prompts_map：对象，分类到提示词映射
- global：对象，common_subject、global_style、negative_prompt
- prompts：对象，保留 default_style、default_negative_prompt 兼容生成流程

## 文件
- 主文件：backend/config.json
- 示例文件：backend/config.example.json
- 本地覆盖：backend/config.local.json（可创建并覆盖任意键）

## 模式切换
- 修改 backend/config.local.json 中的 operation_mode
- 可热重载，或重启后端生效

## 统一运行时配置 API
- GET /api/config/runtime：返回 models、categories、prompts、global 与 source
- GET /api/config/global：返回全局默认
- PUT /api/config/global：更新全局默认

## CRUD API
- 模型：GET/POST/PUT/DELETE /api/models
- 分类：GET/POST/DELETE /api/categories
- 提示词：GET/POST/PUT/DELETE /api/prompts

## 已知限制
- JSON 不支持注释，详细说明参考 config.example.json 的 docs 字段
- 删除分类将级联删除对应提示词
- 数据库模式需保证 SQLite 可写
