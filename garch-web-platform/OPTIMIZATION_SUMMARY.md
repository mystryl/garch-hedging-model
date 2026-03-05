# GARCH Web 平台优化总结

## 优化完成日期
2026-03-05

---

## 优化内容

### 1. 统一性能指标汇总表格为"传统套保" vs "动态套保"

**问题**: 报告和表格中使用了"未套保"vs"套保后"的标签，不够准确。

**解决方案**: 将所有表格列标题和标签统一更新为：
- "未套保" → "传统套保 (h=1)"
- "套保后" → "动态套保 (GARCH)"

**修改文件**:
- `lib/basic_garch_analyzer/report_generator.py`
  - HTML 报告表格列标题（第694行）
  - HTML 指标卡片标题（第659、663行）
- `lib/basic_garch_analyzer/analyzer.py`
  - CSV/Excel 报告列名（第204-218行）

**验证**: ✓ 通过
- HTML 表格包含"传统套保 (h=1)"和"动态套保 (GARCH)"
- CSV 报告第一行指标为"总收益率 (传统套保 h=1)"
- 完全移除了旧的"未套保"和"套保后"标签

---

### 2. 修改 ZIP 文件命名为日期+品种+模型组合

**问题**: 原有 ZIP 文件名格式 `{model_type}_report_{timestamp}.zip` 不够友好。

**解决方案**: 改为 `YYYYMMDD_品种_模型名.zip` 格式
- 示例: `20260305_MEG_Basic_GARCH.zip`

**修改文件**:
- `app.py`
  - 添加 `extract_commodity_name()` 函数（第52-82行）
  - 修改 `/api/generate` 端点的 ZIP 文件生成逻辑（第528-540行）

**品种名称识别逻辑**:
```python
def extract_commodity_name(filepath: str, column_mapping: dict) -> str:
    # 从文件名提取品种名
    # meg_full_data.xlsx → MEG
    # pp_data.xlsx → PP
    # 无法识别 → 通用
```

**验证**: ✓ 通过
- 品种名正确提取（MEG、PP、PE、PVC、PTA）
- 日期格式正确（YYYYMMDD，8位数字）
- 模型名正确映射（Basic_GARCH、DCC_GARCH、ECM_GARCH）

---

### 3. 修复前端报告图片路径问题

**问题**: 通过 `/report` 端点访问 HTML 报告时，图片路径 `figures/xxx.png` 无法正确加载。

**原因**: 浏览器尝试从 `http://localhost:5050/figures/xxx.png` 加载，但该路径不存在。

**解决方案**:
1. 在 `/report` 端点中动态修正图片路径
2. 添加 `/report-images/<path:filename>` 路由提供图片服务

**修改文件**:
- `app.py`
  - 修改 `view_report()` 函数，添加图片路径动态修正（第562-597行）
  - 添加 `serve_report_images()` 路由函数（第600-626行）

**实现逻辑**:
```python
# 使用正则表达式替换图片路径
content = re.sub(
    r'src="figures/([^"]+)"',
    lambda m: f'src="/report-images/{report_dir}/figures/{m.group(1)}"',
    content
)

# 新路由提供图片服务
@app.route('/report-images/<path:filename>')
def serve_report_images(filename):
    # 安全验证后返回图片文件
    return send_file(file_path)
```

**验证**: ✓ 通过
- 图片路径正确转换为 `/report-images/{report_dir}/figures/xxx.png`
- 支持多张图片路径替换
- 包含路径安全检查

---

## 修改文件汇总

| 文件 | 修改内容 | 修改行数 |
|------|---------|---------|
| `lib/basic_garch_analyzer/report_generator.py` | HTML 表格和卡片标题更新 | 2处 |
| `lib/basic_garch_analyzer/analyzer.py` | CSV 报告列名更新 | 1处 |
| `app.py` | 添加品种提取函数 | +31行 |
| `app.py` | 修改 ZIP 文件命名逻辑 | 1处 |
| `app.py` | 修改 /report 端点（图片路径修正） | 重写 |
| `app.py` | 添加 /report-images 路由 | +27行 |

---

## 测试验证

### 测试脚本
- `test_optimizations.py` - 单元测试
- `test_end_to_end.py` - 端到端测试

### 测试结果
✓ 所有测试通过

```
============================================================
✓✓✓ 所有端到端测试通过！ ✓✓✓

优化完成:
  1. ✓ 性能指标表格统一为'传统套保' vs '动态套保'
  2. ✓ ZIP 文件命名为 YYYYMMDD_品种_模型名.zip
  3. ✓ 前端报告图片路径修复（/report-images路由）
============================================================
```

---

## 使用示例

### 生成报告后的 ZIP 文件名
```
20260305_MEG_Basic_GARCH.zip
20260305_PP_DCC_GARCH.zip
20260305_通用_ECM_GARCH.zip
```

### HTML 报告中的表格
```html
<table>
    <tr>
        <th>指标</th>
        <th>传统套保 (h=1)</th>
        <th>动态套保 (GARCH)</th>
    </tr>
    <tr>
        <td>夏普比率</td>
        <td>-0.1234</td>
        <td>0.5678</td>
    </tr>
</table>
```

### 前端访问报告
```
URL: http://localhost:5050/report?path=web_reports/report.html

原始图片路径（在HTML文件中）:
  <img src="figures/1_price_series.png">

修正后的路径（浏览器接收）:
  <img src="/report-images/web_reports/figures/1_price_series.png">
```

---

## 注意事项

1. **品种名称识别**: 如果文件名不包含已知品种（MEG、PP、PE、PVC、PTA），将使用"通用"作为品种名。

2. **报告文件夹**: 报告文件夹保持 `outputs/web_reports/` 不变，只修改下载的 ZIP 文件名。

3. **图片路径安全**: `/report-images` 路由包含完整的安全验证，防止路径遍历攻击。

4. **向后兼容**: HTML 报告文件本身保持不变（图片路径仍为 `figures/xxx.png`），只在通过 Web 服务查看时动态修正。

---

## 下一步建议

1. **允许用户指定品种名**: 当前从文件名自动提取，未来可以在 Web 界面添加"品种名称"输入框。

2. **支持更多品种**: 在 `extract_commodity_name()` 函数中添加更多品种模式。

3. **图片缓存**: 考虑为 `/report-images` 路由添加缓存头，提升性能。

4. **批量下载**: 支持一次下载多个报告的打包 ZIP 文件。
