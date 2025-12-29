# 版本更新说明

## v2.3.0 - 2025-12-29
- 前端：分类选择改为单选并默认选中「环境」，移除多选逻辑
- 前端：根据模型动态调整每类图片数量上限
  - Wan 2.6 上限为 2 张
  - Z-Image 上限为 4 张
- 前端：数量输入框与提示文案联动当前模型上限；启动任务时按上限夹取
- 后端：修复记录写入与 items 落库问题，确保
  - items 条数与成功生成图片数一致
  - 每条 items 正确关联对应的 record_id
  - record.item_count 与实际 items 数量保持一致
- 后端：新增完整性校验接口 GET /api/records/{id}/validate
- 测试：新增集成测试脚本 python_scripts/integration_test_items_integrity.py 验证多图片场景下记录与子项一致性

本次修复解决了：
1) 根据模型不同而最大上限生成图片数量不正确的问题  
2) 数据库记录的 items 计数与关联不一致的问题

## v2.3.1 - 2025-12-29
- 前端：菜单分类与提示词改为接口驱动，保留本地枚举回退
- 前端：严格单选分类、默认「环境」，数量输入联动后端上限并夹取
- 前端：新增模态弹窗（遮罩、ESC关闭、动画、响应式）、Toast 通知与保存全量配置
- 后端：新增 POST /api/config/update 统一保存入口；新增 GET /api/config/limits 返回模型上限
- 测试：新增后端单元测试覆盖配置保存与上限接口

## v2.3.2 - 2025-12-29
- 修复：模型生成图片数量的上限设置
  - 后端：持久化模型上限到数据库 models.max_limit，并提供 GET /api/config/limits、POST /api/config/update（兼容别名在 models_controller）
  - 前端：获取/保存上限支持降级与容错，数量输入与批量生成严格夹取当前模型上限

## v2.3.3 - 2025-12-29
- 新增：图片详情视图支持正向/反向提示词展示与复制
- 新增：提示词中英互译（后端 Qwen），前端一键翻译按钮与加载态/错误提示
- 新增：按文件名查询图片详情接口 GET /api/images/by-filename/{filename}/details?category=...
- 优化：右侧原图展示支持缩放、拖动、双击复位；移动端上下布局
- 辅助：环境检查脚本 scripts/env_check.sh 与 /health/env 环境摘要接口
