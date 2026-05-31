# PPT 共创界面改进总体规划

> **文档版本**：v1.0 | **创建日期**：2026-05-31
> **状态**：第一阶段开发中

---

## 一、项目概述

### 1.1 项目目标

将 PPT 共创界面从"AI工具"升级为"AI伙伴"，实现更智能、更自然的人机协作体验。

### 1.2 核心价值

1. **智能主动**：AI 主动发现机会，提出建议
2. **深度理解**：AI 理解内容本质、用户意图、设计原则
3. **自然协作**：像与人类专家协作一样自然
4. **能力放大**：放大用户的创意和效率

### 1.3 成功指标

| 指标 | 当前基准 | 目标值 |
|------|----------|--------|
| 任务完成时间 | 10分钟 | 6分钟 |
| 操作步骤数 | 8步 | 4步 |
| 用户满意度 | 3.5/5 | 4.5/5 |
| 建议采纳率 | N/A | 60% |

---

## 二、改进方案总览

### 2.1 功能矩阵

| 功能 | 用户价值 | 技术复杂度 | 优先级 | 阶段 |
|------|----------|------------|--------|------|
| 智能上下文感知 | 高 | 高 | P0 | 第一阶段 |
| AI主动建议模式 | 高 | 中 | P0 | 第一阶段 |
| 多轮对话式协作 | 高 | 中 | P0 | 第一阶段 |
| 渐进式生成模式 | 中 | 中 | P1 | 第二阶段 |
| 风格一致性保障 | 中 | 中 | P1 | 第二阶段 |
| 智能内容分析面板 | 中 | 低 | P1 | 第二阶段 |
| 智能检查和修复 | 中 | 中 | P2 | 第三阶段 |
| 智能内容补全 | 中 | 中 | P2 | 第三阶段 |
| 风格模板库 | 低 | 低 | P2 | 第三阶段 |
| 实时协作模式 | 高 | 高 | P3 | 第四阶段 |

### 2.2 依赖关系

```
智能上下文感知 (P0-1)
    ├── AI主动建议 (P0-2)
    ├── 多轮对话协作 (P0-3)
    │       └── 渐进式生成 (P1-4)
    ├── 风格一致性 (P1-5)
    │       └── 智能检查 (P2-7)
    └── 内容分析面板 (P1-6)
            └── 内容补全 (P2-8)
```

---

## 三、第一阶段：智能基础（1-2周）

### 3.1 功能清单

#### 3.1.1 智能上下文感知

**目标**：AI 理解整个 PPT 的结构和主题，而不仅仅是当前幻灯片。

**核心能力**：
- PPT 结构分析
- 内容重复检测
- 逻辑关系理解
- 风格一致性检测

**API 接口**：
- `POST /api/ppt/analyze` - 内容分析
- `POST /api/ppt/style/check` - 风格检查

#### 3.1.2 AI 主动建议模式

**目标**：AI 自动分析内容，主动推荐最佳展示方式。

**核心能力**：
- 内容类型检测
- 展示方式推荐
- 建议气泡 UI

**API 接口**：
- `POST /api/ppt/suggest` - 获取建议

#### 3.1.3 多轮对话式协作

**目标**：支持多轮对话，AI 可以追问、澄清、提供选项。

**核心能力**：
- 对话上下文管理
- 追问和澄清
- 选项提供

**API 接口**：
- `POST /api/ppt/chat` - 多轮对话
- `POST /api/session/create` - 创建会话
- `GET /api/session/{id}` - 获取会话状态

### 3.2 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    第一阶段技术架构                           │
├─────────────────────────────────────────────────────────────┤
│  UI 层                                                      │
│  ├── SuggestionBubble - 建议气泡组件                         │
│  ├── ContextPanel - 上下文显示面板                           │
│  └── ChatInterface - 对话界面                                │
├─────────────────────────────────────────────────────────────┤
│  业务逻辑层                                                  │
│  ├── ContextAnalyzer - 上下文分析器                          │
│  ├── SuggestionEngine - 建议引擎                             │
│  └── ConversationManager - 对话管理器                        │
├─────────────────────────────────────────────────────────────┤
│  API 层                                                      │
│  ├── /api/ppt/analyze - 内容分析                             │
│  ├── /api/ppt/suggest - 获取建议                             │
│  ├── /api/ppt/chat - 多轮对话                                │
│  └── /api/internal/* - 内部测试接口                          │
├─────────────────────────────────────────────────────────────┤
│  数据层                                                      │
│  ├── PPTContext - PPT 上下文数据                             │
│  ├── ConversationState - 对话状态                            │
│  └── SessionManager - 会话管理                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 开发计划

#### 第1天：智能上下文感知模块

**任务**：
1. 创建 `ContextAnalyzer` 类
2. 实现 PPT 结构分析
3. 实现内容类型检测
4. 实现风格一致性检测

**输出**：
- `ppt_cocreation/context_analyzer.py`
- 单元测试

#### 第2天：AI 主动建议模块

**任务**：
1. 创建 `SuggestionEngine` 类
2. 实现建议生成逻辑
3. 实现建议排序和筛选

**输出**：
- `ppt_cocreation/suggestion_engine.py`
- 单元测试

#### 第3天：多轮对话模块

**任务**：
1. 创建 `ConversationManager` 类
2. 实现对话上下文管理
3. 实现选项生成逻辑

**输出**：
- `ppt_cocreation/conversation_manager.py`
- 单元测试

#### 第4天：API 接口实现

**任务**：
1. 实现 `/api/ppt/analyze` 接口
2. 实现 `/api/ppt/suggest` 接口
3. 实现 `/api/ppt/chat` 接口
4. 实现内部测试接口

**输出**：
- 更新 `smart_copilot_api.py`
- API 测试

#### 第5天：UI 组件实现

**任务**：
1. 实现 `SuggestionBubble` 组件
2. 实现 `ContextPanel` 组件
3. 集成到现有 UI

**输出**：
- `ppt_cocreation/suggestion_bubble.py`
- `ppt_cocreation/context_panel.py`
- UI 测试

#### 第6-7天：集成测试和优化

**任务**：
1. 集成测试
2. 性能优化
3. Bug 修复
4. 文档更新

**输出**：
- 集成测试报告
- 性能测试报告
- 更新文档

---

## 四、API 设计摘要

### 4.1 外部 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/ppt/analyze` | POST | 内容分析 |
| `/api/ppt/suggest` | POST | AI 主动建议 |
| `/api/ppt/chat` | POST | 多轮对话 |
| `/api/ppt/check` | POST | 智能检查 |
| `/api/ppt/optimize` | POST | 内容优化 |
| `/api/ppt/generate` | POST | 渐进式生成 |
| `/api/ppt/style/check` | POST | 风格一致性 |
| `/api/ppt/complete` | POST | 内容补全 |

### 4.2 内部 API（AI 自调用后门）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/internal/test` | POST | 功能测试 |
| `/api/internal/verify` | POST | 结果验证 |
| `/api/internal/benchmark` | POST | 性能基准 |
| `/api/internal/debug` | POST | 调试接口 |
| `/api/internal/self-check` | GET | 自检接口 |

### 4.3 会话管理 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/session/create` | POST | 创建会话 |
| `/api/session/{id}` | GET | 获取会话状态 |
| `/api/session/{id}/context` | PATCH | 更新上下文 |

---

## 五、数据模型

### 5.1 核心模型

```python
class PPTContext(BaseModel):
    """PPT 上下文"""
    title: Optional[str]
    theme: Optional[str]
    total_slides: int
    current_slide: int
    slides: List[SlideData]
    metadata: Optional[Dict[str, Any]]

class ConversationState(BaseModel):
    """对话状态"""
    session_id: str
    turn_count: int
    last_action: Optional[str]
    pending_confirm: Optional[Dict[str, Any]]
    history: List[Dict[str, Any]]

class Suggestion(BaseModel):
    """建议"""
    id: str
    type: SuggestionType
    title: str
    description: str
    preview: Optional[Dict[str, Any]]
    confidence: float
    action: Dict[str, Any]
```

### 5.2 枚举类型

```python
class ContentType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    FLOWCHART = "flowchart"
    IMAGE = "image"
    LIST = "list"

class SuggestionType(str, Enum):
    CONTENT_OPTIMIZE = "content_optimize"
    VISUAL_ENHANCE = "visual_enhance"
    STRUCTURE_IMPROVE = "structure_improve"
    STYLE_CONSISTENT = "style_consistent"
```

---

## 六、文件结构

```
ppt_cocreation/
├── __init__.py
├── cocreation_dialog.py      # 主对话框
├── source_panel.py           # 原文面板
├── outline_panel.py          # 大纲面板
├── preview_panel.py          # 预览面板
├── ai_chat_widget.py         # AI 对话组件
├── source_matcher.py         # 原文匹配器
├── context_analyzer.py       # [新增] 上下文分析器
├── suggestion_engine.py      # [新增] 建议引擎
├── conversation_manager.py   # [新增] 对话管理器
├── suggestion_bubble.py      # [新增] 建议气泡组件
└── context_panel.py          # [新增] 上下文面板
```

---

## 七、测试策略

### 7.1 单元测试

每个模块都有对应的单元测试：

```python
# test_context_analyzer.py
def test_analyze_content_type():
    analyzer = ContextAnalyzer()
    result = analyzer.analyze("产品A销量100万，产品B销量200万")
    assert result.content_type == "data_comparison"

def test_detect_style_inconsistency():
    analyzer = ContextAnalyzer()
    slides = [
        {"style": {"primary_color": "#4da6ff"}},
        {"style": {"primary_color": "#ff6b6b"}}
    ]
    result = analyzer.check_style_consistency(slides)
    assert result.consistent == False
```

### 7.2 集成测试

```python
# test_integration.py
def test_suggest_api():
    response = client.post("/api/ppt/suggest", json={
        "context": {"slides": [...]},
        "focus": "visual_enhance"
    })
    assert response.status_code == 200
    assert len(response.json()["suggestions"]) > 0
```

### 7.3 AI 自调用测试

```python
# test_ai_self_test.py
def test_ai_self_test():
    """AI 自动测试建议功能"""
    test_cases = [...]
    response = client.post("/api/internal/test", json={
        "test_suite": "ppt_suggestions",
        "test_cases": test_cases
    })
    assert response.json()["summary"]["failed"] == 0
```

---

## 八、风险与缓解

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| AI 响应延迟 | 用户体验差 | 中 | 流式响应、缓存、异步处理 |
| 上下文理解错误 | 错误建议 | 中 | 用户确认、多方案选择、撤销机制 |
| 状态管理复杂 | 开发困难 | 高 | 状态机模式、模块化设计、充分测试 |

### 8.2 用户体验风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| AI 过度主动 | 用户反感 | 中 | 可控性、关闭选项、学习用户偏好 |
| 学习曲线陡峭 | 用户流失 | 低 | 渐进式披露、引导教程、简单模式 |

---

## 九、下一步行动

### 9.1 立即行动（今天）

1. ✅ 创建整合文档（本文档）
2. ⏳ 开始实现 `ContextAnalyzer` 模块
3. ⏳ 创建单元测试框架

### 9.2 本周计划

1. 完成智能上下文感知模块
2. 完成 AI 主动建议模块
3. 完成多轮对话模块
4. 实现 API 接口
5. 实现 UI 组件

### 9.3 下周计划

1. 集成测试
2. 性能优化
3. Bug 修复
4. 文档更新
5. 准备第二阶段

---

## 十、相关文档

1. `PPT_CoCreation_Improvement_Strategy.md` - 改进策略方案
2. `PPT_CoCreation_UI_Improvement_Detailed.md` - 详细设计方案
3. `PPT_CoCreation_API_Design.md` - API 接口设计
4. `PPT_CoCreation_Improvement_Plan.md` - 改进计划

---

## 十一、变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-05-31 | v1.0 | 创建整合文档，开始第一阶段开发 | AI Assistant |