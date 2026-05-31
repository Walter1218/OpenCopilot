# PPT 共创界面改进 API 设计

> **文档性质**：API 接口设计文档
> **目标读者**：后端开发、前端开发、AI 工程师
> **设计原则**：RESTful、可扩展、AI 可自调用

---

## 一、API 架构概述

### 1.1 设计目标

1. **统一接口**：所有 PPT 共创功能通过统一 API 暴露
2. **AI 可调用**：预留内部接口，AI 可自主调用进行测试和验证
3. **会话管理**：支持多轮对话和上下文保持
4. **流式支持**：支持流式响应，提升用户体验

### 1.2 API 分层

```
┌─────────────────────────────────────────────────────────────┐
│                    PPT 共创 API 架构                         │
├─────────────────────────────────────────────────────────────┤
│  外部 API（用户调用）                                         │
│  ├── /api/ppt/suggest      - AI 主动建议                     │
│  ├── /api/ppt/analyze      - 内容分析                        │
│  ├── /api/ppt/generate     - 渐进式生成                      │
│  ├── /api/ppt/check        - 智能检查                        │
│  └── /api/ppt/optimize     - 内容优化                        │
├─────────────────────────────────────────────────────────────┤
│  内部 API（AI 自调用）                                        │
│  ├── /api/internal/test    - 功能测试                        │
│  ├── /api/internal/verify  - 结果验证                        │
│  ├── /api/internal/benchmark - 性能基准                      │
│  └── /api/internal/debug   - 调试接口                        │
├─────────────────────────────────────────────────────────────┤
│  会话管理                                                     │
│  ├── /api/session/create   - 创建会话                        │
│  ├── /api/session/{id}     - 会话操作                        │
│  └── /api/session/{id}/context - 上下文管理                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、数据模型定义

### 2.1 基础模型

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

# ==========================================
# 枚举类型
# ==========================================

class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    TABLE = "table"
    CHART = "chart"
    FLOWCHART = "flowchart"
    IMAGE = "image"
    LIST = "list"

class ChartType(str, Enum):
    """图表类型"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"

class SuggestionType(str, Enum):
    """建议类型"""
    CONTENT_OPTIMIZE = "content_optimize"  # 内容优化
    VISUAL_ENHANCE = "visual_enhance"      # 视觉增强
    STRUCTURE_IMPROVE = "structure_improve" # 结构改进
    STYLE_CONSISTENT = "style_consistent"  # 风格一致

class CheckSeverity(str, Enum):
    """检查严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

# ==========================================
# 请求模型
# ==========================================

class SlideData(BaseModel):
    """幻灯片数据"""
    index: int = Field(..., description="幻灯片索引")
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="内容")
    layout: Optional[str] = Field("center", description="布局类型")
    items: Optional[List[Dict[str, Any]]] = Field([], description="内容项列表")
    style: Optional[Dict[str, Any]] = Field(None, description="样式配置")

class PPTContext(BaseModel):
    """PPT 上下文"""
    title: Optional[str] = Field(None, description="PPT 标题")
    theme: Optional[str] = Field("corporate", description="主题")
    total_slides: int = Field(0, description="总幻灯片数")
    current_slide: int = Field(0, description="当前幻灯片索引")
    slides: List[SlideData] = Field([], description="所有幻灯片数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ConversationState(BaseModel):
    """对话状态"""
    session_id: str = Field(..., description="会话 ID")
    turn_count: int = Field(0, description="对话轮次")
    last_action: Optional[str] = Field(None, description="上次操作")
    pending_confirm: Optional[Dict[str, Any]] = Field(None, description="待确认项")
    history: List[Dict[str, Any]] = Field([], description="对话历史")

# ==========================================
# 响应模型
# ==========================================

class Suggestion(BaseModel):
    """建议"""
    id: str = Field(..., description="建议 ID")
    type: SuggestionType = Field(..., description="建议类型")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    preview: Optional[Dict[str, Any]] = Field(None, description="预览数据")
    confidence: float = Field(0.8, description="置信度")
    action: Dict[str, Any] = Field(..., description="执行动作")

class CheckResult(BaseModel):
    """检查结果"""
    id: str = Field(..., description="检查项 ID")
    severity: CheckSeverity = Field(..., description="严重程度")
    category: str = Field(..., description="检查类别")
    message: str = Field(..., description="检查消息")
    slide_index: Optional[int] = Field(None, description="相关幻灯片索引")
    suggestion: Optional[Suggestion] = Field(None, description="修复建议")

class AnalysisResult(BaseModel):
    """分析结果"""
    content_type: ContentType = Field(..., description="内容类型")
    key_points: List[str] = Field([], description="关键点")
    data_extracted: Optional[Dict[str, Any]] = Field(None, description="提取的数据")
    recommended_visual: Optional[ContentType] = Field(None, description="推荐的可视化方式")
    quality_score: float = Field(0.0, description="质量评分")
    suggestions: List[Suggestion] = Field([], description="优化建议")
```

---

## 三、外部 API 接口

### 3.1 AI 主动建议 API

#### `POST /api/ppt/suggest`

**描述**：AI 分析当前幻灯片内容，主动提供优化建议

**请求**：
```json
{
  "context": {
    "title": "产品介绍",
    "slides": [
      {
        "index": 0,
        "title": "核心优势",
        "content": "性能提升30%，成本降低20%，用户满意度95%"
      }
    ],
    "current_slide": 0
  },
  "focus": "visual_enhance",  // 可选，关注点
  "max_suggestions": 3         // 最大建议数
}
```

**响应**：
```json
{
  "suggestions": [
    {
      "id": "suggest_001",
      "type": "visual_enhance",
      "title": "数据可视化建议",
      "description": "当前内容包含3个关键指标，建议使用柱状图进行对比展示",
      "preview": {
        "chart_type": "bar",
        "labels": ["性能", "成本", "满意度"],
        "data": [30, 20, 95]
      },
      "confidence": 0.92,
      "action": {
        "type": "convert_to_chart",
        "params": {
          "slide_index": 0,
          "chart_type": "bar",
          "data": {
            "title": "核心优势对比",
            "labels": ["性能提升", "成本降低", "用户满意度"],
            "datasets": [{"label": "百分比", "data": [30, 20, 95]}]
          }
        }
      }
    }
  ],
  "analysis": {
    "content_type": "text",
    "quality_score": 0.75,
    "key_points": ["性能提升30%", "成本降低20%", "用户满意度95%"]
  }
}
```

---

### 3.2 内容分析 API

#### `POST /api/ppt/analyze`

**描述**：深度分析幻灯片内容，识别内容类型和结构

**请求**：
```json
{
  "content": "张三今年25岁，在北京工作，月薪1.5万\n李四今年30岁，在上海工作，月薪2万",
  "context": {
    "title": "员工信息"
  }
}
```

**响应**：
```json
{
  "content_type": "person_attributes",
  "confidence": 0.92,
  "key_points": ["张三今年25岁", "在北京工作", "月薪1.5万"],
  "entities": [],
  "recommended_visual": "table",
  "quality_score": 0.85,
  "suggestions": [
    {
      "type": "visual_enhance",
      "title": "表格展示建议",
      "description": "检测到人物属性数据，建议转换为表格展示",
      "confidence": 0.95
    }
  ]
}
```

**支持的人物属性格式**：
- 标准格式：`姓名：张三，年龄：30岁，职位：工程师`
- 自然语言：`张三，男，30岁，工程师`
- 描述性：`客户王女士今年45岁，是一位企业家`
- 括号格式：`张三（工程师，30岁）`
- 空格分隔：`张三 30岁 工程师`

---

### 3.3 渐进式生成 API

#### `POST /api/ppt/generate`

**描述**：流式生成 PPT 内容，支持渐进式更新

**请求**：
```json
{
  "session_id": "session_001",
  "instruction": "创建一个产品介绍PPT，包含封面、产品特点、优势对比、客户案例、总结",
  "context": {
    "title": "智能助手产品介绍",
    "theme": "tech_blue"
  },
  "stream": true
}
```

**响应**（流式）：
```
data: {"type": "progress", "slide_index": 0, "status": "generating", "message": "正在生成封面..."}
data: {"type": "slide", "slide_index": 0, "data": {"title": "智能助手", "subtitle": "让工作更高效"}}
data: {"type": "progress", "slide_index": 1, "status": "generating", "message": "正在生成产品特点..."}
data: {"type": "slide", "slide_index": 1, "data": {"title": "产品特点", "items": ["智能分析", "自动化处理", "实时协作"]}}
data: {"type": "complete", "total_slides": 5, "message": "生成完成"}
```

---

### 3.4 智能检查 API

#### `POST /api/ppt/check`

**描述**：检查 PPT 质量，发现问题并提供修复建议

**请求**：
```json
{
  "context": {
    "title": "产品介绍",
    "slides": [
      {"index": 0, "title": "封面", "content": "产品介绍"},
      {"index": 1, "title": "产品特点", "content": "特点1\n特点2\n特点3\n特点4\n特点5\n特点6\n特点7"}
    ]
  },
  "checks": ["content_quality", "style_consistency", "logical_flow"]
}
```

**响应**：
```json
{
  "results": [
    {
      "id": "check_001",
      "severity": "warning",
      "category": "content_quality",
      "message": "第2页内容过多（7个要点），建议精简到5个以内",
      "slide_index": 1,
      "suggestion": {
        "id": "fix_001",
        "type": "content_optimize",
        "title": "精简内容",
        "description": "合并或删除部分要点",
        "action": {
          "type": "simplify_content",
          "params": {"slide_index": 1, "max_points": 5}
        }
      }
    },
    {
      "id": "check_002",
      "severity": "info",
      "category": "style_consistency",
      "message": "整体风格一致",
      "slide_index": null,
      "suggestion": null
    }
  ],
  "summary": {
    "total_checks": 3,
    "passed": 2,
    "warnings": 1,
    "errors": 0,
    "quality_score": 0.85
  }
}
```

---

### 3.5 内容优化 API

#### `POST /api/ppt/optimize`

**描述**：优化幻灯片内容，提升表达和视觉效果

**请求**：
```json
{
  "slide": {
    "index": 2,
    "title": "我们的优势",
    "content": "我们的产品很好，很多人都喜欢用，因为确实不错"
  },
  "optimization": ["language", "visual", "structure"]
}
```

**响应**：
```json
{
  "optimized_slide": {
    "index": 2,
    "title": "核心竞争优势",
    "content": "产品性能卓越，用户满意度高达95%，市场占有率领先",
    "items": [
      {"icon": "⚡", "text": "性能卓越：处理速度提升30%"},
      {"icon": "❤️", "text": "用户认可：满意度高达95%"},
      {"icon": "🏆", "text": "市场领先：占有率第一"}
    ]
  },
  "changes": [
    {"field": "title", "old": "我们的优势", "new": "核心竞争优势", "reason": "更专业"},
    {"field": "content", "old": "...", "new": "...", "reason": "更具体、量化"}
  ],
  "quality_improvement": 0.25
}
```

---

### 3.6 多轮对话 API

#### `POST /api/ppt/chat`

**描述**：支持多轮对话，AI 可以追问、澄清、提供选项

**请求**：
```json
{
  "session_id": "session_001",
  "message": "把这个内容做成图表",
  "context": {
    "current_slide": 2,
    "slides": [
      {"index": 2, "content": "Q1增长10%，Q2增长15%，Q3增长20%，Q4增长25%"}
    ]
  }
}
```

**响应**：
```json
{
  "session_id": "session_001",
  "response": "我检测到这是时间序列数据，适合用折线图展示趋势。请问：",
  "options": [
    {"id": "opt_1", "text": "折线图（展示增长趋势）", "action": {"type": "convert_to_chart", "chart_type": "line"}},
    {"id": "opt_2", "text": "柱状图（对比各季度）", "action": {"type": "convert_to_chart", "chart_type": "bar"}},
    {"id": "opt_3", "text": "饼图（展示各季度占比）", "action": {"type": "convert_to_chart", "chart_type": "pie"}}
  ],
  "context_update": {
    "pending_confirm": {"type": "chart_selection", "data": "Q1增长10%，Q2增长15%，Q3增长20%，Q4增长25%"}
  }
}
```

#### `GET /api/ppt/chat/{session_id}/history`

**描述**：获取指定会话的对话历史

**请求**：
```
GET /api/ppt/chat/session_001/history
```

**响应**：
```json
{
  "session_id": "session_001",
  "history": [
    {
      "role": "user",
      "content": "把这个内容做成图表",
      "timestamp": "2026-05-31T01:30:00"
    },
    {
      "role": "assistant",
      "content": "我检测到这是时间序列数据，适合用折线图展示趋势。",
      "timestamp": "2026-05-31T01:30:01"
    }
  ],
  "total_messages": 2
}
```

---

### 3.7 风格一致性 API

#### `POST /api/ppt/style/check`

**描述**：检查整个 PPT 的风格一致性

**请求**：
```json
{
  "context": {
    "slides": [
      {"index": 0, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
      {"index": 1, "style": {"primary_color": "#ff6b6b", "font": "宋体"}},
      {"index": 2, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}}
    ]
  }
}
```

**响应**：
```json
{
  "consistent": false,
  "issues": [
    {
      "slide_index": 1,
      "issue": "配色不一致",
      "expected": "#4da6ff",
      "actual": "#ff6b6b",
      "suggestion": {
        "action": "fix_style",
        "params": {"slide_index": 1, "primary_color": "#4da6ff"}
      }
    },
    {
      "slide_index": 1,
      "issue": "字体不一致",
      "expected": "微软雅黑",
      "actual": "宋体",
      "suggestion": {
        "action": "fix_style",
        "params": {"slide_index": 1, "font": "微软雅黑"}
      }
    }
  ],
  "recommended_style": {
    "primary_color": "#4da6ff",
    "font": "微软雅黑",
    "usage_count": 2
  }
}
```

---

### 3.8 内容补全 API

#### `POST /api/ppt/complete`

**描述**：根据上下文智能补全内容

**请求**：
```json
{
  "context": {
    "title": "产品介绍",
    "current_slide": {
      "index": 3,
      "title": "核心优势",
      "partial_content": "性能提升"
    }
  },
  "completion_type": "bullet_points",
  "max_items": 5
}
```

**响应**：
```json
{
  "completions": [
    "性能提升30%，响应时间缩短50%",
    "成本降低20%，资源利用率提高40%",
    "用户满意度提升至95%",
    "支持1000+并发，稳定性99.9%",
    "部署时间从2周缩短至2天"
  ],
  "confidence": 0.88,
  "context_relevance": 0.92
}
```

---

## 四、内部 API 接口（AI 自调用后门）

### 4.1 功能测试 API

#### `POST /api/internal/test`

**描述**：AI 自主调用，测试各项功能是否正常工作

**请求**：
```json
{
  "test_suite": "ppt_suggestions",
  "test_cases": [
    {
      "name": "数据内容检测",
      "input": {
        "content": "产品A销量100万，产品B销量200万",
        "expected_type": "data_comparison"
      }
    }
  ],
  "auto_fix": true
}
```

**响应**：
```json
{
  "test_id": "test_001",
  "results": [
    {
      "name": "数据内容检测",
      "status": "passed",
      "actual": {"content_type": "data_comparison", "confidence": 0.95},
      "expected": {"content_type": "data_comparison"},
      "duration_ms": 45
    }
  ],
  "summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "duration_ms": 45
  }
}
```

---

### 4.2 结果验证 API

#### `POST /api/internal/verify`

**描述**：AI 验证自己的输出结果是否正确

**请求**：
```json
{
  "action": "convert_to_table",
  "input": "张三25岁北京，李四30岁上海",
  "output": {
    "columns": ["姓名", "年龄", "城市"],
    "rows": [["张三", "25", "北京"], ["李四", "30", "上海"]]
  },
  "validation_rules": [
    {"rule": "row_count", "expected": 2},
    {"rule": "column_count", "expected": 3},
    {"rule": "data_integrity", "check": "all_cells_filled"}
  ]
}
```

**响应**：
```json
{
  "valid": true,
  "checks": [
    {"rule": "row_count", "passed": true, "actual": 2, "expected": 2},
    {"rule": "column_count", "passed": true, "actual": 3, "expected": 3},
    {"rule": "data_integrity", "passed": true, "empty_cells": 0}
  ],
  "confidence": 0.98
}
```

---

### 4.3 性能基准 API

#### `POST /api/internal/benchmark`

**描述**：AI 测试各项功能的性能基准

**请求**：
```json
{
  "benchmark": "content_analysis",
  "iterations": 100,
  "test_data": {
    "content": "测试内容...",
    "complexity": "medium"
  }
}
```

**响应**：
```json
{
  "benchmark": "content_analysis",
  "iterations": 100,
  "results": {
    "avg_duration_ms": 45.2,
    "min_duration_ms": 32.1,
    "max_duration_ms": 78.5,
    "p95_duration_ms": 65.3,
    "success_rate": 0.99
  },
  "baseline": {
    "avg_duration_ms": 50.0,
    "improvement": "9.6%"
  }
}
```

---

### 4.4 调试接口 API

#### `POST /api/internal/debug`

**描述**：AI 调试接口，查看内部状态和执行过程

**请求**：
```json
{
  "action": "trace_suggestion",
  "session_id": "session_001",
  "slide_index": 2
}
```

**响应**：
```json
{
  "trace_id": "trace_001",
  "steps": [
    {"step": 1, "action": "content_analysis", "duration_ms": 12, "result": "text"},
    {"step": 2, "action": "pattern_detection", "duration_ms": 8, "result": "data_comparison"},
    {"step": 3, "action": "suggestion_generation", "duration_ms": 25, "result": "chart_recommendation"}
  ],
  "total_duration_ms": 45,
  "decision_points": [
    {"point": "content_type_detection", "decision": "data_comparison", "confidence": 0.95},
    {"point": "visual_recommendation", "decision": "bar_chart", "confidence": 0.88}
  ]
}
```

---

### 4.5 自检 API

#### `GET /api/internal/self-check`

**描述**：AI 自检各项功能模块是否正常

**响应**：
```json
{
  "status": "healthy",
  "modules": {
    "content_analyzer": {"status": "ok", "version": "1.0.0", "last_check": "2026-05-31T00:05:00"},
    "suggestion_engine": {"status": "ok", "version": "1.0.0", "last_check": "2026-05-31T00:05:00"},
    "style_checker": {"status": "ok", "version": "1.0.0", "last_check": "2026-05-31T00:05:00"},
    "completion_engine": {"status": "degraded", "version": "0.9.0", "last_check": "2026-05-31T00:05:00", "note": "部分功能未实现"}
  },
  "dependencies": {
    "llm_provider": {"status": "ok", "latency_ms": 120},
    "ppt_generator": {"status": "ok", "latency_ms": 50}
  },
  "performance": {
    "avg_response_ms": 45,
    "p99_response_ms": 120,
    "error_rate": 0.01
  }
}
```

---

## 五、会话管理 API

### 5.1 创建会话

#### `POST /api/session/create`

**请求**：
```json
{
  "user_id": "user_001",
  "ppt_context": {
    "title": "产品介绍",
    "slides": []
  }
}
```

**响应**：
```json
{
  "session_id": "session_001",
  "created_at": "2026-05-31T00:05:00",
  "expires_at": "2026-05-31T01:05:00"
}
```

---

### 5.2 获取会话状态

#### `GET /api/session/{session_id}`

**响应**：
```json
{
  "session_id": "session_001",
  "created_at": "2026-05-31T00:05:00",
  "turn_count": 5,
  "context": {
    "current_slide": 2,
    "slides": [...]
  },
  "pending_confirm": null,
  "last_action": "convert_to_table"
}
```

---

### 5.3 更新会话上下文

#### `PATCH /api/session/{session_id}/context`

**请求**：
```json
{
  "operation": "update_slide",
  "params": {
    "slide_index": 2,
    "updates": {
      "title": "新标题",
      "content": "新内容"
    }
  }
}
```

**响应**：
```json
{
  "success": true,
  "updated_context": {...}
}
```

---

## 六、WebSocket API（实时协作）

### 6.1 建立连接

```
ws://localhost:8000/ws/ppt/{session_id}
```

### 6.2 消息格式

**客户端 → 服务端**：
```json
{
  "type": "edit",
  "slide_index": 2,
  "operation": "update_title",
  "data": {"title": "新标题"}
}
```

**服务端 → 客户端**：
```json
{
  "type": "suggestion",
  "suggestion": {
    "id": "suggest_001",
    "type": "visual_enhance",
    "title": "建议转换为图表",
    "action": {...}
  }
}
```

**AI 自调用消息**：
```json
{
  "type": "ai_self_check",
  "action": "verify_suggestion",
  "suggestion_id": "suggest_001",
  "expected_result": {...}
}
```

---

## 七、安全与权限

### 7.1 API 认证

- 外部 API：需要 API Key 或 JWT Token
- 内部 API：仅限本地访问（127.0.0.1）
- WebSocket：需要 Session Token

### 7.2 速率限制

- 外部 API：100 请求/分钟
- 内部 API：无限制（AI 自调用）
- WebSocket：10 消息/秒

### 7.3 数据隔离

- 每个用户的数据独立存储
- 会话数据 24 小时后自动清理
- 敏感数据加密存储

---

## 八、错误处理

### 8.1 错误响应格式

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "输入数据格式错误",
    "details": {
      "field": "slides",
      "reason": "slides 数组不能为空"
    }
  },
  "request_id": "req_001",
  "timestamp": "2026-05-31T00:05:00"
}
```

### 8.2 错误码定义

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| INVALID_INPUT | 400 | 输入数据格式错误 |
| UNAUTHORIZED | 401 | 未授权 |
| SESSION_NOT_FOUND | 404 | 会话不存在 |
| RATE_LIMITED | 429 | 请求过于频繁 |
| INTERNAL_ERROR | 500 | 内部服务器错误 |
| AI_SERVICE_ERROR | 503 | AI 服务不可用 |

---

## 九、AI 自调用示例

### 9.1 AI 自动测试建议功能

```python
# AI 内部调用示例
async def ai_self_test_suggestions():
    """AI 自动测试建议功能"""
    
    # 1. 准备测试数据
    test_cases = [
        {
            "name": "数据内容检测",
            "input": {"content": "产品A销量100万，产品B销量200万"},
            "expected": {"type": "data_comparison", "visual": "bar_chart"}
        },
        {
            "name": "流程内容检测",
            "input": {"content": "第一步：需求分析\n第二步：设计\n第三步：开发"},
            "expected": {"type": "process", "visual": "flowchart"}
        }
    ]
    
    # 2. 调用测试 API
    response = await api_client.post("/api/internal/test", {
        "test_suite": "ppt_suggestions",
        "test_cases": test_cases,
        "auto_fix": True
    })
    
    # 3. 验证结果
    if response["summary"]["failed"] > 0:
        # 自动修复或调整
        await ai_self_fix(response["results"])
    
    return response
```

### 9.2 AI 自动验证输出

```python
# AI 验证自己的输出
async def ai_verify_output(action, input_data, output_data):
    """AI 验证自己的输出是否正确"""
    
    response = await api_client.post("/api/internal/verify", {
        "action": action,
        "input": input_data,
        "output": output_data,
        "validation_rules": [
            {"rule": "data_integrity", "check": "all_cells_filled"},
            {"rule": "format_correct", "check": "valid_json"}
        ]
    })
    
    if not response["valid"]:
        # 重新生成或调整
        await ai_self_correct(action, input_data, response["checks"])
    
    return response
```

### 9.3 AI 自动性能监控

```python
# AI 监控自己的性能
async def ai_monitor_performance():
    """AI 监控自己的性能"""
    
    # 1. 运行基准测试
    benchmark = await api_client.post("/api/internal/benchmark", {
        "benchmark": "content_analysis",
        "iterations": 100
    })
    
    # 2. 检查是否退化
    if benchmark["results"]["avg_duration_ms"] > benchmark["baseline"]["avg_duration_ms"] * 1.2:
        # 性能退化超过 20%，触发优化
        await ai_self_optimize()
    
    # 3. 自检
    self_check = await api_client.get("/api/internal/self-check")
    
    return {
        "benchmark": benchmark,
        "self_check": self_check
    }
```

---

## 十、实施建议

### 10.1 分阶段实施

**第一阶段（1-2周）**：
- 实现基础 API：suggest、analyze、check
- 实现会话管理
- 实现内部测试 API

**第二阶段（2-3周）**：
- 实现渐进式生成
- 实现风格一致性
- 实现内容优化

**第三阶段（3-4周）**：
- 实现内容补全
- 实现 WebSocket 实时协作
- 完善内部调试 API

### 10.2 技术栈

- **Web 框架**：FastAPI
- **数据验证**：Pydantic
- **异步支持**：asyncio
- **WebSocket**：FastAPI WebSocket
- **文档生成**：Swagger UI / ReDoc

### 10.3 监控与日志

- 请求日志：记录所有 API 调用
- 性能监控：响应时间、错误率
- AI 自调用日志：记录 AI 的自检和测试结果

---

## 十一、总结

这个 API 设计的核心特点：

1. **完整的功能覆盖**：10 个功能模块都有对应的 API
2. **AI 可自调用**：预留内部 API，AI 可以自主测试、验证、调试
3. **会话管理**：支持多轮对话和上下文保持
4. **流式支持**：支持渐进式生成和实时反馈
5. **安全可控**：内外部 API 分离，权限明确

通过这个 API 设计，AI 可以：
- 自主测试各项功能
- 验证自己的输出
- 监控自己的性能
- 自动发现和修复问题

这为实现真正的"AI 伙伴"提供了技术基础。