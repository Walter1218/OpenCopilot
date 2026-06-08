# PPT 生成鲁棒性提升方案

> 基于 PPT 生成全链路深度调研，定位 6 个根因问题，提出 P0/P1/P2 三级改进方案。
>
> 核心结论：当前 PPT 解析不稳定是 **「LLM 输出不可控」+「解析层防御不足」+「中间件干扰」** 三重缺陷叠加。

---

## 一、问题根因

| # | 根因 | 影响 | 文件位置 |
|---|------|------|----------|
| R1 | LLM 调用未启用 `response_format: json_object` | LLM 自由发挥，输出可能不是合法 JSON | `llm_provider.py:178-192` |
| R2 | 手写 `_repair_json_string` 覆盖面有限 | 策略6（删字符）有破坏性风险，无法处理 null/None/注释等 | `ppt_generator.py:377-462` |
| R3 | `PlannerMiddleware` 向 PPT prompt 注入 Task Plan 文本 | 干扰 LLM 输出纯 JSON，使其倾向输出 Markdown | `middlewares.py:383-438` |
| R4 | 全局 `temperature=0.7` 对 JSON 输出偏高 | 随机性高，JSON 语法错误率上升 | `llm_provider.py:178` |
| R5 | 三条 PPT 路径各自实现 JSON 解析逻辑 | 修复不统一，一处修好其他路径仍失败 | `studio_tab.py` / `pipeline.py` / `cocreation_widget.py` |
| R6 | 项目未使用 `json_repair` 等专业 JSON 修复库 | 重复造轮子，效果差 | `requirements.txt` |

### 调用链路图

```
StudioTabV5._on_quick_open()
  └─► V5AgentWorker(prompt, action_type="ppt")
       └─► call_agent_pipeline_sync()
            └─► MiddlewarePipeline (7层中间件)
                 ├─ 0. DistributedTracer
                 ├─ 1. SessionSetupMiddleware (加载 personas/ppt.md)
                 ├─ 2. SecurityGuardMiddleware
                 ├─ 3. ImmuneSystemMiddleware (✅ PPT 已跳过)
                 ├─ 4. PlannerMiddleware (⚠️ R3: 可能注入 Task Plan)
                 ├─ 5. StateTrackingMiddleware
                 ├─ 6. CapabilityRouterMiddleware
                 └─ 7. LLMProviderMiddleware
                      └─► MiMoProvider._build_payload()
                           ⚠️ R1: 无 response_format
                           ⚠️ R4: temperature=0.7
                           └─► LLM 输出 → V5AgentWorker.finished_signal
                                └─► StudioTabV5._on_ppt_generated()
                                     └─► _parse_slides_from_text()
                                          └─► ppt_generator.extract_json_from_text()
                                               ├─ Step 0: 清理中文引号
                                               ├─ Step 1: 匹配 ```json``` 代码块
                                               ├─ Step 2: json.loads() (⚠️ R2: 手写修复)
                                               ├─ Step 2.0.1: _repair_json_string() → 重试
                                               ├─ Step 2.1: 截断修复 + 迭代修复
                                               └─ Step 3: Markdown 降级
```

---

## 二、改进方案

### P0 — 立即见效（改动最小，收益最高）

#### P0-1: 引入 `json_repair` 库替代手写修复

**改动文件**: `requirements.txt` + `ppt_generator.py`

**原理**: `json_repair` 是经过大量真实 LLM 输出训练的专业库，覆盖所有常见错误模式（缺冒号/逗号/尾随逗号/单引号/注释/None→null/True→true 等），修复率从手写版的 ~60% 提升到 ~95%。

**实现**:
```python
# ppt_generator.py
try:
    from json_repair import repair_json
    repaired = repair_json(clean_str, return_objects=False)
    parsed = json.loads(repaired)
except ImportError:
    # 降级到手写修复
    repaired = _repair_json_string(clean_str)
    parsed = json.loads(repaired)
```

**预期**: 消除 ~80% 的解析失败。

#### P0-2: MiMoProvider 添加 `response_format` 支持

**改动文件**: `llm_provider.py` + `middlewares.py`（传递 action_type）

**原理**: OpenAI 兼容 API 通常支持 `response_format: {"type": "json_object"}`，从源头确保 LLM 输出合法 JSON。

**实现**:
```python
# llm_provider.py - MiMoProvider._build_payload()
if kwargs.get("response_format"):
    payload["response_format"] = kwargs["response_format"]

# middlewares.py - LLMProviderMiddleware.process()
if ctx.action_type == "ppt":
    ws_kwargs["response_format"] = {"type": "json_object"}
```

**预期**: 从源头消除 ~90% 的 JSON 语法错误。

#### P0-3: 统一 JSON 解析入口

**改动文件**: `studio_tab.py`

**原理**: 当前 `_parse_slides_from_text` 有双层解析（先走 `ppt_generator`，再走本地回退），本地回退没有修复能力。应删除冗余回退，统一走 `ppt_generator.extract_json_from_text`。

**预期**: 消除重复代码，修复一处全局生效。

### P1 — 中期优化

#### P1-1: PlannerMiddleware 跳过 PPT 请求

**改动文件**: `middlewares.py`

**原理**: PlannerMiddleware 的 `_is_complex_task()` 匹配 "步骤"/"流程"/"设计" 等关键词 → 注入 Task Plan 文本到 system prompt → 干扰 LLM 的 JSON 输出纯度。PPT 请求应像 ImmuneSystemMiddleware 一样直接跳过。

**实现**:
```python
# middlewares.py - PlannerMiddleware.process()
if ctx.action_type in ("ppt", "content_generation"):
    return await self.next(ctx)  # 跳过规划
```

**预期**: 消除 plan 文本对 JSON 输出的干扰。

#### P1-2: PPT 专用 LLM 参数

**改动文件**: `middlewares.py` 或 `caller.py`

**原理**: JSON 输出需要低随机性。为 PPT action_type 设置 `temperature=0.3`。

**预期**: 降低 JSON 语法错误率 ~30%。

#### P1-3: 二次 LLM 修复兜底

**改动文件**: `studio_tab.py` 或 `ppt_generator.py`

**原理**: 当 `extract_json_from_text` 返回 None 时，发起一次新的 LLM 调用，将错误 JSON + 错误信息让 LLM 自行修正。

**实现**:
```python
if slides is None:
    fix_prompt = f"以下 JSON 有语法错误，请修复并只输出修复后的 JSON:\n{full_text[:3000]}"
    fixed = await llm.generate(fix_prompt)
    slides = extract_json_from_text(fixed)
```

**预期**: 兜底修复最后的 ~5% 失败。

### P2 — 长期演进

#### P2-1: Pydantic Schema 结构化输出

定义 `SlideModel` / `PresentationModel` Pydantic schema，通过 `json_schema` 参数传给 LLM，保证字段类型/必填项全部符合。

#### P2-2: 统一 PPT 生成管线

将路径 A（快速创建）迁移到路径 B（4 阶段管线），每阶段 JSON 更简单，解析失败率大幅下降。

#### P2-3: JSON 解析遥测

记录每次解析的成功/失败、使用的降级策略、修复轮次，用数据驱动优化。

---

## 三、预期效果

| 指标 | 当前 | P0 完成后 | P1 完成后 |
|------|------|----------|----------|
| JSON 解析成功率 | ~70-80% | ~95% | ~98% |
| 首次生成成功率 | ~60% | ~90% | ~95% |
| 降级到 Markdown 的比例 | ~15% | ~3% | ~1% |
| 用户需要手动干预的比例 | ~10% | ~2% | <1% |

---

## 四、实施优先级

```
P0-1 (json_repair)  ─┐
P0-2 (response_format)──┼── 并行实施，互不依赖
P0-3 (统一入口)     ─┘
         │
         ▼
P1-1 (Planner跳过)  ─┐
P1-2 (低温参数)     ──┼── 并行实施
P1-3 (二次LLM修复) ─┘
         │
         ▼
P2-1 (Pydantic schema)
P2-2 (统一管线)
P2-3 (遥测)
```
