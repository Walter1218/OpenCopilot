# OpenCopilot 办公场景 Prompt 库设计与工具调用能力完善方案

> **设计日期**: 2026-05-27  
> **目标**: 沉淀一套专业的办公场景prompt库，完善工具调用和转化能力

---

## 1. 当前系统分析

### 1.1 现有Persona系统架构

```python
# 当前Persona加载机制
def load_persona(action_type):
    """动态加载 Persona 文件，支持热更新"""
    filepath = os.path.join(os.path.dirname(__file__), "personas", f"{action_type}.md")
    if not os.path.exists(filepath):
        filepath = os.path.join(os.path.dirname(__file__), "personas", "default.md")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()
```

**现有Persona列表**:
- `default.md`: 通用AI助手
- `code.md`: 代码架构师
- `translate.md`: 翻译官
- `polish.md`: 资深编辑
- `custom.md`: 自定义指令修改
- `revision.md`: 文档修订专家

### 1.2 当前不足

1. **Persona数量有限**: 仅有6个基础Persona，缺乏细分场景
2. **Prompt结构简单**: 纯文本指令，缺乏结构化设计
3. **工具调用缺失**: 没有工具调用能力，纯文本生成
4. **场景适配不足**: 缺乏针对不同办公场景的深度优化

---

## 2. 办公场景Prompt库架构设计

### 2.1 目录结构

```
personas/
├── office/                    # 办公场景Persona
│   ├── business/              # 商务场景
│   │   ├── email.md          # 商务邮件
│   │   ├── report.md         # 商务报告
│   │   ├── proposal.md       # 商业提案
│   │   └── meeting.md        # 会议纪要
│   ├── academic/              # 学术场景
│   │   ├── paper.md          # 学术论文
│   │   ├── thesis.md         # 毕业论文
│   │   └── abstract.md       # 摘要写作
│   ├── technical/             # 技术场景
│   │   ├── documentation.md  # 技术文档
│   │   ├── api_doc.md        # API文档
│   │   └── user_manual.md    # 用户手册
│   ├── creative/              # 创意场景
│   │   ├── marketing.md      # 营销文案
│   │   ├── copywriting.md    # 广告文案
│   │   └── content.md        # 内容创作
│   └── legal/                 # 法律场景
│       ├── contract.md       # 合同文档
│       └── compliance.md     # 合规文档
├── translation/               # 翻译场景
│   ├── general.md            # 通用翻译
│   ├── technical.md          # 技术翻译
│   ├── literary.md           # 文学翻译
│   └── business.md           # 商务翻译
├── editing/                   # 编辑场景
│   ├── proofreading.md       # 校对
│   ├── rewriting.md          # 改写
│   ├── simplification.md     # 简化
│   └── formalization.md      # 正式化
└── analysis/                  # 分析场景
    ├── data.md               # 数据分析
    ├── market.md             # 市场分析
    └── competitive.md        # 竞品分析
```

### 2.2 Prompt模板结构

每个Prompt文件采用结构化设计：

```markdown
# [Persona名称]

## 角色定义
你是一个[角色描述]，专注于[领域]。

## 核心能力
1. [能力1]
2. [能力2]
3. [能力3]

## 工作流程
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 输出规范
- [规范1]
- [规范2]
- [规范3]

## 质量标准
- [标准1]
- [标准2]
- [标准3]

## 示例
### 输入示例
[输入内容]

### 输出示例
[输出内容]

## 注意事项
- [注意事项1]
- [注意事项2]
```

---

## 3. 核心办公场景Prompt设计

### 3.1 商务邮件Persona

```markdown
# 商务邮件专家

## 角色定义
你是一个专业的商务邮件撰写专家，精通各种商务场景的邮件写作，包括询价、报价、投诉、感谢、邀请等。

## 核心能力
1. 精准把握商务邮件的正式程度和语气
2. 根据不同场景选择恰当的邮件结构
3. 确保邮件内容清晰、专业、有说服力

## 工作流程
1. 分析邮件目的和受众
2. 确定邮件结构和语气
3. 撰写邮件正文
4. 优化表达和格式

## 输出规范
- 邮件主题：简洁明了，概括核心内容
- 称呼：根据收件人关系选择恰当称呼
- 正文：分段清晰，逻辑连贯
- 结尾：礼貌专业，明确下一步行动
- 签名：包含必要联系信息

## 质量标准
- 语言正式得体，符合商务规范
- 内容完整，无遗漏关键信息
- 逻辑清晰，易于理解
- 无语法错误和拼写错误

## 示例
### 输入示例
写一封询价邮件，询问某产品的价格和交货期。

### 输出示例
主题：关于[产品名称]询价

尊敬的[收件人姓名]：

您好！

我司对贵公司的[产品名称]很感兴趣，希望了解以下信息：
1. 产品单价及批量采购优惠
2. 最小起订量
3. 交货周期
4. 付款方式

请提供详细报价单，如有产品目录或样品，也请一并寄送。

期待您的回复。

此致
敬礼

[您的姓名]
[职位]
[公司名称]
[联系方式]

## 注意事项
- 根据收件人文化背景调整语气
- 避免使用过于口语化的表达
- 确保所有数字和日期准确无误
```

### 3.2 学术论文Persona

```markdown
# 学术论文写作专家

## 角色定义
你是一个学术论文写作专家，精通各学科领域的论文写作规范，包括引言、文献综述、方法论、结果分析、讨论等部分。

## 核心能力
1. 熟悉各学科论文写作规范
2. 掌握学术语言表达技巧
3. 能够进行文献引用和格式规范

## 工作流程
1. 理解论文主题和研究问题
2. 分析论文结构和逻辑
3. 撰写或优化各部分内容
4. 检查学术规范和格式

## 输出规范
- 引言：明确研究背景、问题和意义
- 文献综述：系统梳理相关研究
- 方法论：详细描述研究方法
- 结果：客观呈现研究发现
- 讨论：深入分析结果意义
- 结论：总结研究贡献和局限

## 质量标准
- 语言严谨客观，符合学术规范
- 逻辑清晰，论证充分
- 引用规范，格式正确
- 无抄袭和学术不端

## 注意事项
- 避免主观臆断和情感化表达
- 确保数据准确性和可重复性
- 注意学术伦理和版权问题
```

### 3.3 技术文档Persona

```markdown
# 技术文档专家

## 角色定义
你是一个技术文档写作专家，精通各种技术文档的编写，包括API文档、用户手册、开发指南、部署文档等。

## 核心能力
1. 理解复杂技术概念并清晰表达
2. 掌握技术文档的结构和规范
3. 能够编写准确、易懂的技术内容

## 工作流程
1. 理解技术内容和目标受众
2. 设计文档结构和章节
3. 撰写技术内容
4. 添加示例和图表
5. 审校和完善

## 输出规范
- 概述：简要介绍文档目的和范围
- 前提条件：列出必要的环境和依赖
- 步骤说明：详细的操作步骤
- 示例代码：可运行的代码示例
- 常见问题：FAQ和故障排除
- 参考资料：相关链接和文档

## 质量标准
- 技术准确，无误导性内容
- 步骤清晰，易于跟随
- 示例完整，可直接运行
- 格式规范，易于阅读

## 注意事项
- 避免使用过于专业的术语
- 确保所有代码示例经过测试
- 注意版本兼容性说明
```

---

## 4. 工具调用和转化能力完善

### 4.1 工具调用架构设计

```python
# tools/ 目录结构
tools/
├── __init__.py
├── base.py                    # 工具基类
├── file_tools.py              # 文件处理工具
├── text_tools.py              # 文本处理工具
├── format_tools.py            # 格式转换工具
├── analysis_tools.py          # 分析工具
└── integration_tools.py       # 集成工具

# 工具注册机制
class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, name, tool_class):
        self.tools[name] = tool_class
    
    def get_tool(self, name):
        return self.tools.get(name)
    
    def list_tools(self):
        return list(self.tools.keys())
```

### 4.2 核心工具实现

#### 4.2.1 文件处理工具

```python
# tools/file_tools.py
class FileReadTool:
    """文件读取工具"""
    name = "file_read"
    description = "读取文件内容，支持多种格式"
    
    async def execute(self, file_path, format="text"):
        """执行文件读取"""
        if format == "docx":
            return await self._read_docx(file_path)
        elif format == "pptx":
            return await self._read_pptx(file_path)
        elif format == "pdf":
            return await self._read_pdf(file_path)
        else:
            return await self._read_text(file_path)

class FileWriteTool:
    """文件写入工具"""
    name = "file_write"
    description = "将内容写入文件"
    
    async def execute(self, content, file_path, format="text"):
        """执行文件写入"""
        # 根据格式写入文件
        pass

class FileConvertTool:
    """文件格式转换工具"""
    name = "file_convert"
    description = "转换文件格式"
    
    async def execute(self, input_path, output_format):
        """执行格式转换"""
        # 支持 docx -> pdf, pptx -> pdf, md -> docx 等
        pass
```

#### 4.2.2 文本处理工具

```python
# tools/text_tools.py
class TextExtractTool:
    """文本提取工具"""
    name = "text_extract"
    description = "从各种格式中提取文本"
    
    async def execute(self, content, extract_type="all"):
        """执行文本提取"""
        if extract_type == "headings":
            return self._extract_headings(content)
        elif extract_type == "key_points":
            return self._extract_key_points(content)
        elif extract_type == "summary":
            return self._generate_summary(content)
        else:
            return content

class TextTransformTool:
    """文本转换工具"""
    name = "text_transform"
    description = "转换文本格式和风格"
    
    async def execute(self, text, transform_type):
        """执行文本转换"""
        if transform_type == "formal":
            return await self._make_formal(text)
        elif transform_type == "casual":
            return await self._make_casual(text)
        elif transform_type == "concise":
            return await self._make_concise(text)
        elif transform_type == "detailed":
            return await self._make_detailed(text)
        else:
            return text
```

#### 4.2.3 格式转换工具

```python
# tools/format_tools.py
class MarkdownToDocxTool:
    """Markdown转Word工具"""
    name = "md_to_docx"
    description = "将Markdown转换为Word文档"
    
    async def execute(self, md_content, output_path):
        """执行转换"""
        # 使用python-docx生成Word文档
        pass

class MarkdownToPptxTool:
    """Markdown转PPT工具"""
    name = "md_to_pptx"
    description = "将Markdown转换为PPT演示文稿"
    
    async def execute(self, md_content, output_path, template=None):
        """执行转换"""
        # 使用python-pptx生成PPT
        pass

class TextToTableTool:
    """文本转表格工具"""
    name = "text_to_table"
    description = "将结构化文本转换为表格"
    
    async def execute(self, text, format="markdown"):
        """执行转换"""
        # 解析文本并生成表格
        pass
```

### 4.3 工具调用集成

```python
# 在asu_custom_agent.py中集成工具调用
class ToolCallingAgent:
    """支持工具调用的Agent"""
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        self.tool_registry.register("file_read", FileReadTool())
        self.tool_registry.register("file_write", FileWriteTool())
        self.tool_registry.register("file_convert", FileConvertTool())
        self.tool_registry.register("text_extract", TextExtractTool())
        self.tool_registry.register("text_transform", TextTransformTool())
        self.tool_registry.register("md_to_docx", MarkdownToDocxTool())
        self.tool_registry.register("md_to_pptx", MarkdownToPptxTool())
        self.tool_registry.register("text_to_table", TextToTableTool())
    
    async def process_with_tools(self, request):
        """处理带工具调用的请求"""
        # 解析请求中的工具调用意图
        tool_calls = self._parse_tool_calls(request)
        
        # 执行工具调用
        results = []
        for tool_call in tool_calls:
            tool = self.tool_registry.get_tool(tool_call["name"])
            if tool:
                result = await tool.execute(**tool_call["params"])
                results.append(result)
        
        # 将工具结果注入到prompt中
        enriched_request = self._enrich_with_tool_results(request, results)
        
        # 调用LLM生成最终结果
        return await self._call_llm(enriched_request)
```

### 4.4 工具调用Prompt设计

```markdown
# 工具调用指南

## 可用工具列表

### 文件处理工具
- `file_read`: 读取文件内容
  - 参数: file_path (文件路径), format (格式: text/docx/pptx/pdf)
  - 返回: 文件内容

- `file_write`: 写入文件
  - 参数: content (内容), file_path (文件路径), format (格式)
  - 返回: 写入结果

- `file_convert`: 格式转换
  - 参数: input_path (输入路径), output_format (输出格式)
  - 返回: 转换后的文件路径

### 文本处理工具
- `text_extract`: 文本提取
  - 参数: content (内容), extract_type (提取类型: all/headings/key_points/summary)
  - 返回: 提取的文本

- `text_transform`: 文本转换
  - 参数: text (文本), transform_type (转换类型: formal/casual/concise/detailed)
  - 返回: 转换后的文本

### 格式转换工具
- `md_to_docx`: Markdown转Word
  - 参数: md_content (Markdown内容), output_path (输出路径)
  - 返回: Word文档路径

- `md_to_pptx`: Markdown转PPT
  - 参数: md_content (Markdown内容), output_path (输出路径), template (模板)
  - 返回: PPT文件路径

## 工具调用格式

```json
{
  "tool_calls": [
    {
      "name": "tool_name",
      "params": {
        "param1": "value1",
        "param2": "value2"
      }
    }
  ]
}
```

## 使用示例

### 场景: 将会议纪要转换为PPT

**用户请求**: "将这份会议纪要转换为PPT演示文稿"

**工具调用**:
```json
{
  "tool_calls": [
    {
      "name": "text_extract",
      "params": {
        "content": "会议纪要内容...",
        "extract_type": "key_points"
      }
    },
    {
      "name": "md_to_pptx",
      "params": {
        "md_content": "提取的关键点...",
        "output_path": "/path/to/output.pptx"
      }
    }
  ]
}
```
```

---

## 5. 实现路线图

### 5.1 第一阶段：Prompt库建设（1-2周）

1. **创建目录结构**
   ```
   personas/office/
   personas/translation/
   personas/editing/
   personas/analysis/
   ```

2. **编写核心Persona**
   - 商务邮件、报告、提案
   - 学术论文、摘要
   - 技术文档、API文档
   - 翻译场景（通用、技术、商务）

3. **优化现有Persona**
   - 增强translate.md的翻译能力
   - 增强polish.md的润色能力
   - 增强revision.md的修订能力

### 5.2 第二阶段：工具调用能力（2-3周）

1. **创建工具框架**
   ```
   tools/
   ├── __init__.py
   ├── base.py
   ├── file_tools.py
   ├── text_tools.py
   ├── format_tools.py
   ```

2. **实现核心工具**
   - 文件读写工具
   - 文本提取工具
   - 格式转换工具

3. **集成到Agent**
   - 修改asu_custom_agent.py
   - 添加工具调用解析
   - 实现工具结果注入

### 5.3 第三阶段：场景优化（1-2周）

1. **场景测试**
   - 测试各种办公场景
   - 收集用户反馈
   - 优化Prompt效果

2. **性能优化**
   - 优化工具调用效率
   - 减少不必要的文件操作
   - 实现缓存机制

3. **用户体验**
   - 添加工具调用进度提示
   - 优化错误处理
   - 提供使用指南

---

## 6. Prompt库管理机制

### 6.1 热更新机制

```python
class PersonaManager:
    """Persona管理器，支持热更新"""
    
    def __init__(self, personas_dir="personas"):
        self.personas_dir = personas_dir
        self.personas_cache = {}
        self.last_reload_time = 0
    
    def get_persona(self, persona_name, reload_interval=300):
        """获取Persona，支持定时热更新"""
        current_time = time.time()
        
        # 检查是否需要重新加载
        if current_time - self.last_reload_time > reload_interval:
            self._reload_personas()
            self.last_reload_time = current_time
        
        return self.personas_cache.get(persona_name, self._load_default())
    
    def _reload_personas(self):
        """重新加载所有Persona"""
        self.personas_cache.clear()
        for root, dirs, files in os.walk(self.personas_dir):
            for file in files:
                if file.endswith(".md"):
                    persona_name = os.path.splitext(file)[0]
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.personas_cache[persona_name] = f.read().strip()
```

### 6.2 Persona选择机制

```python
def select_persona(action_type, context_source, user_preference=None):
    """根据上下文智能选择Persona"""
    
    # 1. 优先使用用户指定的Persona
    if user_preference:
        return user_preference
    
    # 2. 根据action_type选择
    persona_mapping = {
        "translate": "translation/general",
        "code": "code",
        "polish": "editing/proofreading",
        "custom": "custom",
        "revision": "revision",
        "email": "office/business/email",
        "report": "office/business/report",
        "paper": "office/academic/paper",
        "technical": "office/technical/documentation",
    }
    
    if action_type in persona_mapping:
        return persona_mapping[action_type]
    
    # 3. 根据context_source选择
    source_mapping = {
        "ide": "code",
        "browser": "default",
        "drag": "default",
        "chat": "default",
    }
    
    return source_mapping.get(context_source, "default")
```

---

## 7. 总结

### 7.1 核心价值

1. **专业化**: 针对不同办公场景提供专业的Prompt
2. **结构化**: 采用统一的Prompt模板结构
3. **可扩展**: 支持热更新和动态加载
4. **工具集成**: 支持工具调用，提升处理能力

### 7.2 差异化优势

1. **场景深度**: 深度适配各种办公场景
2. **工具能力**: 支持文件处理、格式转换等工具调用
3. **本地化**: 完全本地运行，保护隐私
4. **热更新**: 支持Prompt热更新，无需重启

### 7.3 短期目标

1. 建立核心办公场景Prompt库（10-15个核心Persona）
2. 实现基础工具调用能力（文件读写、格式转换）
3. 优化现有翻译和润色能力
4. 提供用户友好的Persona选择机制

通过这套Prompt库和工具调用能力，OpenCopilot将成为一个真正专业的办公助手，能够处理各种复杂的办公场景需求。