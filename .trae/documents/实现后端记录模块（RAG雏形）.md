## 目标与范围
- 在后端实现“记录模块”，对每次生成任务的输入、经 Qwen 优化后的提示词、生成参数与输出图片信息进行严格校验与持久化，形成面向后续 RAG/统计的高质量原始数据。
- 存储介质为按日归档的 JSON Lines 文件（NDJSON），路径 backend/data/raw/yyyy-mm-dd.json；支持高并发追加写入、文件锁定、缓冲队列、性能与错误日志、周期归档。

## 架构设计
- 服务层：RecordService（单例，后台写线程 + 归档线程）
  - 公开方法：add_record(job_meta, items) 将一批生成记录入队；shutdown() 刷盘并安全退出。
  - 组件：
    - Writer：队列消费，批量落盘（NDJSON，一条记录一行）；fcntl.flock 保证并发安全；O_APPEND + fsync 保证原子性。
    - Archiver：定时压缩历史文件（gzip/tar.gz），移动至 backend/data/archive/。
    - Validator：基于 Pydantic 的模型校验，补充正则与范围检查。
- 模型层：RecordEntry（整体对象）与 GeneratedItem（生成记录子项）
  - 使用 Pydantic 字段别名将英文属性序列化为中文键，确保 JSON 可序列化/反序列化。
- 集成点：
  - generate_controller：读取前端头部 X-User-ID、X-Session-ID（缺省写 "-1"），把用户信息与请求参数传入 job_context。
  - _task_generator：生成 task_params 时已含最终正向/反向提示词与种子/温度/top_p；汇总为 job_meta。
  - background_task_service：在并行执行收集到 results 后，调用 RecordService.add_record(job_meta, items)。

## 数据模型与字段校验
- RecordEntry（中文别名字段，严格校验）：
  - 用户ID: string|null（空或缺省写 "-1"）
  - SessionID: string|null（空或缺省写 "-1"）
  - 创建时间: UTC，格式 yyyymmddhh24（例如 20250130T08 写为 2025013008）
  - 通用基础提示词: 非空字符串
  - 分类描述提示词: 非空字符串
  - 优化后正向提示词: 非空字符串（来自 Qwen refine）
  - 优化后反向提示词: 字符串，可为空（可为空字符串）
  - 比例: 字符串，正则 ^\d{1,3}:\d{1,3}$（如 16:9）
  - 画质: 枚举 {"1K","2K","4K","HD"}（可扩展）
  - 数量: 正整数（>=1）；与 GenerateRequest.count 一致
  - 模型名称: 非空字符串
  - 生成记录: 数组 GeneratedItem
- GeneratedItem：
  - 随机种子: string（由 int 转字符串）
  - 热度值: float（temperature）范围校验：来自 Settings.parameters.temperature_range
  - top值: float（top_p）范围校验：来自 Settings.parameters.top_p_range
  - 相对url路径: string（如 /api/images/{id}/raw）；校验前缀 ^/api/images/ 及 /raw|/thumb 结尾之一
  - 存储绝对路径: string（必须为绝对路径，os.path.isabs）
- URL与路径：
  - 若第三方返回完整 URL，仅用于内部验证；最终入库以相对路径为准（与 [DashScopeClient.to_data_url_if_local](file:///home/ubuntu/codes/z_image_make/backend/services/dashscope_client_service.py#L378-L404) 保持一致）。

## 存储格式与文件策略
- 文件路径：backend/data/raw/yyyy-mm-dd.json（按服务端 UTC 日期计算）
- 文件存在检查：首次写入自动创建目录与文件。
- 追加写入：NDJSON（每条记录一行）；单次写入为完整 JSON 字符串 + "\n"。
- 并发锁定：
  - Linux 环境使用 fcntl.flock(LOCK_EX) 包裹写操作，确保同进程多线程与多进程安全。
  - 打开模式 "a"（O_APPEND）；写后 flush + os.fsync，避免数据丢失。
- 原子性：单条记录写入为不可分割块（append+lock），异常回滚由队列重试承担。

## 缓冲队列与性能
- 队列：queue.Queue(maxsize=10_000)，生产者阻塞避免 OOM。
- 批量落盘：每批 N=100 或 T=500ms 触发刷盘（可按需调节）。
- 指标：
  - perf 日志：队列长度、批量大小、单批耗时、失败重试次数。
  - error 日志：校验失败、写入异常、归档异常。
  - op 日志：文件轮换、压缩完成、启动/停止事件。

## 归档与生命周期
- 归档策略：每日 02:00 扫描 raw 目录，压缩非今日文件至 archive/yyyy-mm-dd.json.gz；完成后保留或移动源文件（默认移动）。
- 清理策略：保留最近 N=30 天原始与归档；超期删除（可配置）。
- 启停：
  - main.startup_event：RecordService.start()（与 [start_job_dispatcher](file:///home/ubuntu/codes/z_image_make/backend/services/background_task_service.py#L32-L36) 同步启动）。
  - main.shutdown_event：RecordService.shutdown()，确保最后一批刷盘与归档安全完成。

## 集成实施步骤
1. 新增文件
   - backend/services/record_service.py：RecordService 单例、Writer/Archiver 线程、锁与落盘逻辑、日志。
   - backend/models/record_models.py：Pydantic 模型（RecordEntry/GeneratedItem），中文别名与校验器。
   - backend/utils/validators.py：常用正则与范围校验函数（比例、URL、路径）。
2. 接入 generate_controller
   - 读取 X-User-ID、X-Session-ID 头；缺省记为 "-1"。
   - 在提交后台任务时，构造 job_meta：用户信息、时间戳、原始提示词/分类、比例与画质、数量、模型名称。
   - 参考 [generate_controller.generate](file:///home/ubuntu/codes/z_image_make/backend/controllers/generate_controller.py#L115-L136)。
3. 接入 _task_generator
   - 已有 Qwen 优化逻辑与参数生成（见 [task_generator](file:///home/ubuntu/codes/z_image_make/backend/controllers/generate_controller.py#L19-L79)）。
   - 将 final_positive_prompt/final_negative_prompt 写入 job_meta，用于记录。
4. 接入 background_task_service
   - 在收集 results 阶段，把每个 result 转换为 GeneratedItem：
     - 相对url路径：originalUrl 或 url（优先 raw，再次 thumb）；
     - 存储绝对路径：saved_path；
     - 随机种子、热度值、top值来自对应 task_params。
   - 调用 RecordService.add_record(job_meta, items)（见 [任务收集点](file:///home/ubuntu/codes/z_image_make/backend/services/background_task_service.py#L131-L155)）。
5. main 启停接入
   - 在 [startup_event](file:///home/ubuntu/codes/z_image_make/backend/main.py#L38-L55) 启动记录模块；在 [shutdown_event](file:///home/ubuntu/codes/z_image_make/backend/main.py#L57-L64) 安全停止。

## 数据验证与完整性
- 必填非空：通用基础提示词、分类描述提示词、优化后正向提示词、模型名称；数量>=1。
- 枚举值：画质限定集合，参数可来自 Settings.parameters 以便扩展。
- 范围：temperature/top_p 基于配置 ranges 校验，超出则拒绝并记录 error 日志。
- URL/路径：相对路径前缀与绝对路径 isabs 校验；非法则拒绝入库。
- 完整性校验：
  - 为每行记录计算 SHA256，追加写入同名 .sha256 索引文件（一行一个摘要，与行号对应）。
  - 提供 verify(day) 工具方法，逐行比对，输出错误报告与统计。

## 日志与监控
- 使用标准 logging（项目现用），命名 logger：record_service、record_archiver。
- 输出分类：
  - 操作日志（info）：文件创建、轮换、归档完成。
  - 错误日志（error）：校验错误、写入失败、锁异常。
  - 性能日志（debug/info）：批量大小、耗时、队列深度、归档用时。

## 扩展性与预留接口
- StorageBackend 抽象：JSONFileStorageBackend（当前实现）；未来可扩展 S3/对象存储/分布式文件系统。
- 统计接口预留：record_service 提供 iterator(day) 与 summary(day) 便于后续 /api/records 统计端点实现。
- 字段扩展：Pydantic 模型允许新增字段，别名与默认值兼容旧数据。

## 测试与验证
- 单元测试：
  - 校验器测试（比例、画质、URL/路径、范围）。
  - 写入原子性测试：并发 20 线程入队，最终行数与摘要一致。
  - 归档测试：构造多日数据，验证压缩与移动。
- 集成测试：
  - 调用 /api/generate（wan/z_image），等待完成后读取当日 raw 文件验证条目与摘要。
- 运行期验证：设置 debug 日志，观察批量刷盘与队列指标。

## 变更影响与兼容性
- 不改动现有响应协议；仅在后端内部新增记录能力。
- 读取用户/会话信息通过头部，前端可渐进集成；缺省使用 "-1"。