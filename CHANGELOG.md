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
