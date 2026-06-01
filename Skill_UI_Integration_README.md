# 技能UI集成功能使用指南

> **版本**：v1.0 | **日期**：2026-06-01

---

## 一、功能概述

技能UI集成功能为OpenCopilot提供了完整的技能管理和调用界面，包括：

1. **技能面板**：可视化浏览和执行所有技能
2. **技能搜索**：快速搜索和调用技能
3. **右键菜单**：根据上下文智能推荐相关技能
4. **快捷指令**：支持`/skill_name`格式的命令
5. **快捷键**：Ctrl+K、Ctrl+/、Ctrl+Shift+S

---

## 二、快速开始

### 2.1 启动演示

```bash
cd /Users/onetwo/Documents/trae_projects/OpenCopilot
python demo_skill_ui.py
```

### 2.2 运行测试

```bash
python test_skill_ui_integration.py
```

---

## 三、功能使用说明

### 3.1 技能面板

**打开方式**：
- 点击主界面第4个Tab "⚡ 技能中心"
- 或按 `Ctrl+Shift+S`

**功能**：
- 浏览所有可用技能
- 按类别筛选技能
- 搜索特定技能
- 查看技能详情
- 执行技能

### 3.2 技能搜索

**打开方式**：
- 按 `Ctrl+K`
- 或点击搜索按钮

**使用方法**：
1. 输入关键词搜索技能
2. 在结果列表中选择技能
3. 查看技能详情
4. 点击"执行"按钮执行技能

### 3.3 右键菜单

**使用方法**：
1. 在文本编辑器中选中文本
2. 右键点击选中的文本
3. 在"🎯 技能推荐"子菜单中选择相关技能
4. 点击技能执行相应操作

**特性**：
- 根据选中内容智能推荐技能
- 支持多种上下文类型（文本、代码、文件）
- 动态更新菜单项

### 3.4 快捷指令

**使用方法**：
1. 在对话输入框中输入`/`命令
2. 按Enter执行命令

**命令格式**：
- `/skill_name` - 执行技能
- `/skill_name:intent` - 执行特定意图
- `/skill_name param=value` - 带参数执行

**示例**：
```
/coding - 执行编程技能
/knowledge:query - 查询知识库
/ppt:generate - 生成PPT
/evaluation - 执行评估技能
/file - 执行文件技能
/format - 执行格式转换技能
/persona - 执行角色技能
```

### 3.5 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+K` | 打开技能搜索对话框 |
| `Ctrl+/` | 打开技能命令输入 |
| `Ctrl+Shift+S` | 切换到技能中心Tab |

---

## 四、技能列表

### 4.1 编程技能（CodingSkill）

**功能**：
- 代码审查
- Bug修复
- 代码解释
- 代码重构
- 代码分析

**命令**：
```
/coding
/coding:review
/coding:bug_fix
/coding:explain
/coding:refactor
/coding:analyze
```

### 4.2 知识技能（KnowledgeSkill）

**功能**：
- 知识图谱查询
- 实体搜索
- 知识导出
- 知识构建

**命令**：
```
/knowledge
/knowledge:query
/knowledge:search_entity
/knowledge:export
/knowledge:build
```

### 4.3 PPT技能（PPTSkill）

**功能**：
- PPT生成
- PPT建议
- PPT检查
- PPT分析

**命令**：
```
/ppt
/ppt:generate
/ppt:suggest
/ppt:check
/ppt:analyze
```

### 4.4 评估技能（EvaluationSkill）

**功能**：
- 内容评价
- 翻译评价
- 代码评价
- 质量检查

**命令**：
```
/evaluation
/evaluation:evaluate
/evaluation:score
/evaluation:quality_check
```

### 4.5 文件技能（FileSkill）

**功能**：
- 文件读取
- 文件写入
- 目录列表
- 文件删除

**命令**：
```
/file
/file:read
/file:write
/file:list
/file:delete
```

### 4.6 格式技能（FormatSkill）

**功能**：
- 文本转表格
- Markdown转Word
- Markdown转PPT

**命令**：
```
/format
/format:text_to_table
/format:md_to_docx
/format:md_to_pptx
```

### 4.7 角色技能（PersonaSkill）

**功能**：
- 人设列表
- 获取人设
- 保存人设
- 删除人设

**命令**：
```
/persona
/persona:list
/persona:get
/persona:save
/persona:delete
```

---

## 五、常见问题

### 5.1 技能面板不显示

**可能原因**：
- Skill注册失败
- 依赖库缺失

**解决方案**：
1. 检查控制台错误信息
2. 确保所有依赖库已安装
3. 重启应用程序

### 5.2 右键菜单不显示技能推荐

**可能原因**：
- 选中文本为空
- IntentRouter未正确初始化

**解决方案**：
1. 确保选中了文本
2. 检查SkillRegistry是否正确初始化
3. 查看控制台错误信息

### 5.3 命令解析失败

**可能原因**：
- 命令格式错误
- 技能名称不存在

**解决方案**：
1. 检查命令格式是否正确
2. 使用`/help`查看所有可用技能
3. 尝试模糊匹配

### 5.4 快捷键不响应

**可能原因**：
- 快捷键冲突
- 焦点不在正确位置

**解决方案**：
1. 检查是否有其他程序占用快捷键
2. 确保焦点在应用程序窗口内
3. 尝试重启应用程序

---

## 六、开发说明

### 6.1 文件结构

```
widgets/
├── skill_panel.py          # 技能面板UI组件
├── skill_context_menu.py   # 技能增强版右键菜单
└── skill_search_dialog.py  # 技能搜索对话框

smart_copilot.py            # 主UI集成
test_skill_ui_integration.py # 测试脚本
demo_skill_ui.py            # 演示脚本
```

### 6.2 扩展技能

要添加新技能，请按照以下步骤：

1. 在`skill_architecture/`目录创建新的Skill类
2. 继承`BaseSkill`基类
3. 实现必要的方法
4. 在`smart_copilot.py`的`_init_skills`方法中注册新技能

### 6.3 自定义右键菜单

要自定义右键菜单，请修改`widgets/skill_context_menu.py`中的：

- `_build_text_menu()`：文本菜单
- `_build_code_menu()`：代码菜单
- `_build_file_menu()`：文件菜单

### 6.4 添加快捷键

要在`smart_copilot.py`中添加新快捷键，请在`_setup_shortcuts`方法中添加：

```python
from PyQt6.QtGui import QShortcut, QKeySequence

shortcut = QShortcut(QKeySequence("Your_Key_Sequence"), self)
shortcut.activated.connect(your_function)
```

---

## 七、技术细节

### 7.1 信号连接

```python
# 技能执行信号
skill_panel.skill_execute.connect(self._on_skill_execute)
skill_search_dialog.skill_execute.connect(self._on_skill_execute)
skill_context_menu.skill_execute.connect(self._on_skill_execute)

# 右键菜单动作信号
skill_context_menu.action_triggered.connect(self._on_context_menu_action)
```

### 7.2 上下文传递

```python
context = SkillContext(
    intent=intent,
    input_data={
        "selected_text": selected_text,
        "context_source": context_source,
        "file_path": file_path,
        "language": language
    }
)
```

### 7.3 异步执行

```python
import asyncio
import threading

async def execute_skill():
    result = await skill.execute(context)
    return result

def run_async():
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(execute_skill())
    loop.close()
    
    # 在主线程中更新UI
    QMetaObject.invokeMethod(self, "_on_skill_result", Qt.ConnectionType.QueuedConnection)

thread = threading.Thread(target=run_async)
thread.daemon = True
thread.start()
```

---

## 八、更新日志

### v1.0 (2026-06-01)
- 实现技能面板UI组件
- 实现技能增强版右键菜单
- 实现技能搜索对话框
- 集成到主UI
- 添加快捷键支持
- 创建测试和演示脚本

---

## 九、联系方式

如有问题或建议，请联系开发团队。

---

*文档最后更新：2026-06-01*