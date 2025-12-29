## 概览
- 目标：将前端硬编码配置迁移到后端，持久化到数据库并提供 CRUD；新增 operation_mode（database｜config_file）与健壮回退机制；完善测试与文档。
- 影响面：后端（controllers/services/db/config/tests）、前端（App.tsx 首屏加载与 CRUD 交互）、配置文件（config.json/config.example.json）。

## 数据模型与存储（SQLite）
- 新增/更新表（在 [connection.py](file:///home/ubuntu/codes/z_image_make/backend/db/connection.py#L14-L51) 的 init_db 中创建）：
  - models(id TEXT PRIMARY KEY, name TEXT, provider TEXT, model_name TEXT, description TEXT, enabled INTEGER DEFAULT 1)
  - categories(name TEXT PRIMARY KEY)
  - prompts(category TEXT PRIMARY KEY REFERENCES categories(name) ON DELETE CASCADE, prompt TEXT NOT NULL)
  - global_settings(id INTEGER PRIMARY KEY CHECK(id=1), common_subject TEXT, global_style TEXT, negative_prompt TEXT)
- 首次启动 seed：若数据库为空，写入默认数据（与 config_file 一致）：
  - models：Wan 2.6、Z-Image Turbo
  - categories：取自 [types.ts](file:///home/ubuntu/codes/z_image_make/types.ts#L2-L10)
  - prompts：INITIAL_PROMPTS 映射
  - global_settings：commonSubject、globalStyle、negativePrompt 默认值

## 统一运行时配置与回退机制
- 配置参数
  - 在 [settings.py](file:///home/ubuntu/codes/z_image_make/backend/config/settings.py) 增加 Settings.operation_mode 属性，支持 'database'｜'config_file'，默认 'config_file'。
  - 非法值：logger.warning 并强制回退到 'config_file'。
- 统一配置服务（runtime_config_service）
  - 读取顺序：
    - operation_mode=database → 从 DB 读取 models/categories/prompts/global；DB 异常或空则回退。
    - operation_mode=config_file → 读取 config.json；缺键时以 config.example.json 兜底。
  - 返回统一结构：
    - models: ModelInfo[]（id/name/provider/model_name/description/enabled）
    - categories: string[]
    - prompts: Record<string,string>
    - global: { common_subject, global_style, negative_prompt }
- 配置文件结构调整
  - 扩展 [config.json](file:///home/ubuntu/codes/z_image_make/backend/config.json)：新增 models[]、categories[]、prompts 映射与 global 对象，结构与 DB 一致。
  - 注释与说明：JSON 不支持注释，使用 [config.example.json](file:///home/ubuntu/codes/z_image_make/backend/config.example.json) 提供 JSONC 风格示例或在各块添加 docs 字段，详细说明用途与取值范围。
- 与现有生成流程兼容
  - [generate_controller.py](file:///home/ubuntu/codes/z_image_make/backend/controllers/generate_controller.py#L39-L53) 仍从 settings.prompts 读取 default_style 和 default_negative_prompt；若 DB 存在 global_settings 则优先该值；保留 [models_controller.get_prompt_config](file:///home/ubuntu/codes/z_image_make/backend/controllers/models_controller.py#L21-L24) 的只读输出。

## 后端路由与服务改造
- 路由（在 [main.py](file:///home/ubuntu/codes/z_image_make/backend/main.py#L85-L93) 注册）：
  - models_controller：扩展为 CRUD
    - GET /api/models → 通过 runtime_config_service 读取
    - POST /api/models → 新增模型
    - PUT /api/models/{id} → 更新模型
    - DELETE /api/models/{id} → 删除模型
  - categories_controller：
    - GET /api/categories
    - POST /api/categories
    - DELETE /api/categories/{name}
  - prompts_controller：
    - GET /api/prompts
    - POST /api/prompts（新增/覆盖）
    - PUT /api/prompts/{category}
    - DELETE /api/prompts/{category}
  - config_controller（global）：
    - GET /api/config/global
    - PUT /api/config/global
- 服务层
  - 新增 model_service、category_service、prompt_service、settings_service（global）：封装 DB 操作与校验。
  - 新增 runtime_config_service：集中来源选择、合并结果与日志记录。

## 前端改造（App.tsx）
- 首屏加载：
  - GET /api/models → setModels（selectedModel 默认第一项）
  - GET /api/categories → setCategories
  - GET /api/prompts → setCatPrompts
  - GET /api/config/global → setCommonSubject / setGlobalStyle / setNegativePrompt
- CRUD 交互：
  - 新增分类：POST /api/categories → 成功后 POST /api/prompts 初始化空提示词
  - 修改提示词：PUT /api/prompts/{category}（保存按钮或输入框失焦自动保存）
  - 删除分类（如需）：DELETE /api/categories/{name}
- 去除硬编码常量：移除 MODELS、INITIAL_CATEGORIES、INITIAL_PROMPTS 与默认字符串；保留类型与现有生成逻辑。

## 单元测试
- 新增 backend/tests/test_operation_mode.py：
  - test_config_file_mode：operation_mode=config_file 时，验证返回内容来自配置文件。
  - test_database_mode：operation_mode=database 时，预置 DB 数据并验证读取。
  - test_invalid_mode_fallback：非法值回退到 config_file 并记录警告日志。
  - test_db_unavailable_fallback：DB 抛错/空数据回退至 config_file。
  - test_config_corrupted：config.json 损坏时使用 example/空对象并记录警告。
- 运行：python -m unittest discover -s backend/tests -p "test_*.py"

## 文档（统一说明）
- 新增/更新 docs/config.md 或 README 配置章节：
  - operation_mode 含义、取值、默认值、风险与回退逻辑。
  - 模式切换操作指南（修改 config.local.json，热重载生效）。
  - 配置结构说明：models/categories/prompts/global 与示例；说明 JSON 无原生注释，推荐查看 example 或 docs 字段。
  - 已知限制与注意事项：
    - 删除分类将级联删除其提示词；
    - DB 模式需确保 SQLite 文件可写与目录存在；
    - 旧接口 /api/config/prompts 为只读兼容；
    - provider 与字段校验严格，写操作需通过服务层校验。

## 交付清单
- 后端：controllers/*（新增 categories/prompts/config，扩展 models）、services/*（新增 5 个服务）、db/connection.py（建表）、config.json｜config.example.json（扩展结构与注释示例）、tests/test_operation_mode.py。
- 前端：App.tsx（改为 API 驱动的首屏加载与 CRUD）。
- 不改动：生成与任务控制器、图片与下载控制器等现有功能保持原状。

## 风险与防护
- 严格输入校验（Pydantic）与事务处理（删除分类→级联删除 prompts）。
- 完整日志输出：非法 operation_mode、DB 异常、文件损坏与回退决策均记录。