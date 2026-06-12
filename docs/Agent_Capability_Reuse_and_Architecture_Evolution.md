# Agent 能力复用与架构演进方案

> 基于 Coding Agent 现有能力（IntentDetector / ToolExecutor / PromptGenerator / CodingAgent）的分析，评估 PPT 等功能是否应在其基础上构建，并给出推荐的架构演进路径。

---

## 一、Coding Agent 现有架构评估

### 1.1 核心设计模式

```
用户输入
  └─► IntentDetector（意图检测）
       ├─ 关键词匹配 → CodingIntent 枚举
       └─ 上下文推断 → diagnostics/git_diff/symbols
  └─► ToolExecutor（上下文收集）
       ├─ IDEToolExecutor → diagnostics + symbol + git_diff（HTTP → IDE 扩展）
       └─ AnalysisToolExecutor → lint + type_check + test + read_file
  └─► PromptGenerator（动态 Prompt 组装）
       ├─ 角色加载（personas/*.md）
       ├─ Bug 类型指导（BUG_TYPE_GUIDES）
       ├─ 语言指导（LANGUAGE_GUIDES）
       └─ 按意图拼装 prompt（fix/review/explain/refactor/analyze）
  └─► LLM 调用
  └─► _parse_*_response（结构化响应解析）
       └─ 按 ### section 分割 Markdown 输出
```

### 1.2 优势

| 模式 | 价值 |
|------|------|
| 意图驱动路由 | 根据意图走不同分支，避免一个大 prompt 处理所有场景 |
| 并行上下文收集 | `asyncio.gather` 同时获取 diagnostics/symbol/git_diff，延迟低 |
| 动态 Prompt 组装 | 针对性 prompt，LLM 输出质量更高 |
| Persona 系统 | 角色定义复用，一处修改全局生效 |

### 1.3 局限

| 问题 | 说明 |
|------|------|
| 领域绑定代码场景 | IntentDetector 的关键词是 "bug"/"error"/"refactor"，不适用于内容生成 |
| ToolExecutor 依赖 IDE | 上下文收集通过 `http://localhost:{port}` 调 IDE 扩展，PPT 场景无 IDE 上下文 |
| 响应解析过于简单 | `_parse_*_response` 只是按 `###` 分割 Markdown，不具备 JSON 修复能力 |
| 无自修复机制 | LLM 输出解析失败后直接返回错误，没有重试或修复流程 |
| 无结构化输出约束 | 没有使用 response_format / json_schema 等约束 LLM 输出格式 |

---

## 二、是否应在 Coding Agent 上构建 PPT 功能

### 结论：**不建议直接复用，但应借鉴其架构模式**

### 理由

**不应该直接复用的原因：**

1. **领域不匹配**
   - `IntentDetector` 检测的是代码意图（bug_fix/review/refactor），PPT 需要的是**内容意图**（数据展示/流程说明/对比分析/总结汇报）
   - 硬套进去会让 `IntentDetector` 变成一个枚举膨胀的怪物

2. **上下文源完全不同**
   - Coding Agent 的上下文 = IDE diagnostics + git diff + symbol info
   - PPT 的上下文 = 文档结构分析（标题层级、数据表、流程步骤、统计数据）
   - 两者没有共用的上下文收集器

3. **Coding Agent 本身也很薄**
   - 解析逻辑只是按 `###` 分割，不比 PPT 当前的解析高明
   - 它的强项是**架构模式**（意图→上下文→Prompt→解析），不是具体实现

**应该借鉴的原因：**

1. **IntentRouter 模式** — PPT 也需要意图路由，但路由的是内容类型（chart/table/flowchart/text），不是代码意图
2. **ContextCollector 模式** — PPT 也需要上下文收集，但收集的是文档结构特征，不是 IDE 诊断
3. **PromptAssembler 模式** — PPT 也需要动态 Prompt，但组装的是版式选型规则 + few-shot 示例，不是 Bug 类型指导
4. **StructuredOutputParser 模式** — PPT 更需要结构化输出解析，但用的是 JSON repair + Pydantic，不是 Markdown section 分割

---

## 三、推荐架构：通用 Agent Pipeline 框架

### 3.1 架构设计

将 Coding Agent 和 PPT 共同的架构模式抽象为通用框架：

```
opencopilot/agent/framework/
├── __init__.py
├── router.py              # IntentRouter — 通用意图路由
├── collector.py           # ContextCollector — 通用上下文收集（抽象基类）
├── assembler.py           # PromptAssembler — 通用 Prompt 组装
├── parser.py              # StructuredOutputParser — 通用结构化输出解析
├── healing.py             # SelfHealingLoop — 自修复循环
└── collectors/            # 领域特定的上下文收集器
     ├── code_collector.py    # 代码场景（复用 coding_agent 的 ToolExecutor）
     └── document_collector.py # 文档场景（PPT/Word/Excel 通用）
```

### 3.2 各模块职责

#### IntentRouter（通用意图路由）

```python
class IntentRouter:
    """根据 action_type 路由到对应的处理管线"""
    
    _routes = {
        "ppt": "document_pipeline",
        "word": "document_pipeline",
        "excel": "document_pipeline",
        "coding": "code_pipeline",
        "chat": "chat_pipeline",
    }
    
    def route(self, action_type: str) -> str:
        return self._routes.get(action_type, "default_pipeline")
```

**与 coding_agent 的区别**：coding_agent 用关键词匹配推断意图（`IntentDetector`），这里用 `action_type` 直接路由（更可靠，因为 GUI 层已经确定了 action_type）。

#### ContextCollector（通用上下文收集）

```python
class ContextCollector(ABC):
    """上下文收集器抽象基类"""
    
    @abstractmethod
    async def collect(self, input_data: Any) -> Dict[str, Any]:
        """收集上下文信息"""
        pass

class DocumentContextCollector(ContextCollector):
    """文档场景上下文收集器"""
    
    async def collect(self, text: str) -> Dict[str, Any]:
        return {
            "structure": self._analyze_structure(text),      # 标题层级
            "data_tables": self._extract_tables(text),       # 数据表
            "processes": self._extract_processes(text),      # 流程步骤
            "statistics": self._extract_statistics(text),    # 统计数据
            "layout_hints": self._suggest_layouts(text),     # 版式建议
            "length": len(text),
            "sections": self._count_sections(text),
        }

class CodeContextCollector(ContextCollector):
    """代码场景上下文收集器（复用 coding_agent 的 ToolExecutor）"""
    
    async def collect(self, file_path: str) -> Dict[str, Any]:
        # 复用现有的 IDEToolExecutor + AnalysisToolExecutor
        return await self.tool_executor.get_full_context(file_path)
```

#### PromptAssembler（通用 Prompt 组装）

```python
class PromptAssembler:
    """根据意图 + 上下文 + 输出格式要求，动态组装 Prompt"""
    
    def assemble(self, intent: str, context: Dict, output_schema: Optional[Dict] = None) -> str:
        parts = []
        parts.append(self._load_persona(intent))         # 角色
        parts.append(self._inject_context(context))       # 上下文
        parts.append(self._inject_rules(intent))          # 规则
        parts.append(self._inject_examples(intent))       # Few-shot 示例
        parts.append(self._inject_schema(output_schema))  # 输出格式约束
        return "\n".join(parts)
```

**与 coding_agent 的区别**：coding_agent 的 `PromptGenerator` 硬编码了 Bug 类型指导和语言指导，这里是规则驱动的，可以按领域注入不同规则。

#### StructuredOutputParser（通用结构化输出解析）

```python
class StructuredOutputParser:
    """通用结构化输出解析，集成 json_repair + Pydantic 校验"""
    
    def parse(self, text: str, schema: Optional[Type[BaseModel]] = None) -> Any:
        # 1. 提取 JSON
        json_str = self._extract_json(text)
        
        # 2. 尝试直接解析
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError:
            # 3. json_repair 修复
            from json_repair import repair_json
            parsed = json.loads(repair_json(json_str, return_objects=False))
        
        # 4. Pydantic 校验（如果提供了 schema）
        if schema:
            return schema.model_validate(parsed)
        
        return parsed
```

**与 coding_agent 的区别**：coding_agent 只按 `###` 分割 Markdown，这里用 json_repair + Pydantic 做真正的结构化解析。

#### SelfHealingLoop（自修复循环）

```python
class SelfHealingLoop:
    """解析失败时，将错误信息 + 原始输出发回 LLM 修复，最多重试 N 次"""
    
    async def execute_with_healing(
        self, 
        llm_call: Callable, 
        parser: StructuredOutputParser,
        max_retries: int = 2
    ) -> Any:
        output = await llm_call()
        
        for attempt in range(max_retries + 1):
            try:
                return parser.parse(output)
            except Exception as e:
                if attempt >= max_retries:
                    raise
                
                # 构造修复 prompt
                fix_prompt = (
                    f"你上次输出的 JSON 有语法错误：{e}\n\n"
                    f"请修复以下 JSON 并只输出修复后的结果：\n"
                    f"{output[:3000]}"
                )
                output = await llm_call(fix_prompt)
```

**coding_agent 完全没有这个能力** — LLM 输出解析失败就直接返回错误。

### 3.3 PPT 场景的应用

```
用户点击"生成PPT"
  └─► IntentRouter: action_type="ppt" → document_pipeline
       │
       ├─ PPTContextCollector.collect(text)
       │    - 分析原文结构（标题层级、段落数量）
       │    - 识别内容类型（统计→chart, 对比→table, 流程→flowchart）
       │    - 提取关键数据点
       │
       ├─ PromptAssembler.assemble("ppt", context)
       │    - 加载 personas/ppt.md
       │    - 注入版式选型规则
       │    - 注入 few-shot JSON 示例
       │    - 注入输出 schema 约束
       │
       ├─ LLM(response_format=json_object, temperature=0.3)
       │
       └─► SelfHealingLoop:
            ├─ StructuredOutputParser.parse(output, PresentationModel)
            │    - json_repair 修复语法
            │    - Pydantic 校验 schema
            └─ 失败？→ 发回 LLM 修复 → 重试（最多 2 次）
```

### 3.4 Coding Agent 的迁移路径

```
当前 coding_agent/              迁移到 framework/
─────────────────              ──────────────────
IntentDetector         →      IntentRouter (action_type 路由)
ToolExecutor           →      CodeContextCollector (复用 IDE 工具)
PromptGenerator        →      PromptAssembler (规则驱动)
_parse_*_response      →      StructuredOutputParser (json_repair + Pydantic)
(无)                   →      SelfHealingLoop (新增)
```

迁移是渐进式的：
1. 先建 framework 骨架
2. PPT 作为第一个使用 framework 的场景
3. Coding Agent 逐步迁移过去（保留 coding_agent/ 作为兼容层）
4. 未来 Word/Excel 等场景直接基于 framework 构建

---

## 四、实施优先级

| 阶段 | 内容 | 前置条件 |
|------|------|----------|
| **Phase 0** | P0 鲁棒性修复（json_repair + response_format + 统一入口） | 无 |
| **Phase 1** | 建立 `opencopilot/agent/framework/` 骨架 | Phase 0 完成 |
| **Phase 2** | PPT 场景接入 framework（DocumentContextCollector + PromptAssembler） | Phase 1 完成 |
| **Phase 3** | Coding Agent 迁移到 framework | Phase 2 验证通过 |
| **Phase 4** | Word/Excel 等场景基于 framework 构建 | Phase 3 完成 |

### 核心原则

> **先治病（Phase 0），再强身（Phase 1-2），最后统一（Phase 3-4）。**

---

## 五、总结

| 问题 | 回答 |
|------|------|
| 是否应在 coding_agent 上构建 PPT？ | **不应该**，领域不匹配，强行复用会导致代码膨胀 |
| 是否应借鉴 coding_agent 的架构？ | **应该**，意图路由→上下文收集→Prompt组装→结构化解析 是好模式 |
| 推荐方向？ | 抽取通用 Agent Pipeline 框架，PPT 作为第一个使用者，Coding Agent 逐步迁移 |
| 什么时候做？ | Phase 0（鲁棒性修复）完成后，作为 Phase 1-2 启动 |
