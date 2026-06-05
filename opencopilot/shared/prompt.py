"""
统一 Prompt 构建服务

所有模块的 prompt 构建逻辑统一在此，确保：
- persona 加载统一
- context_source 处理统一
- persona/context 冲突清理统一

使用方式:
    from prompt_builder import build_full_prompt, load_persona, build_context_prefix
"""

import os
from typing import Optional, Dict, Any


# ==========================================
# Context Source 描述（所有模块共享）
# ==========================================

CONTEXT_DESCRIPTIONS = {
    "ide": (
        "当前用户正在代码编辑器（IDE）中工作。"
        "如果请求中包含 [diagnostics]（诊断报错）或 [git_diff]（版本变更），请重点结合这些信息来分析代码问题或代码变动。"
        "如果请求中包含 [selection]（用户选中的文本片段）或 [content] 只是一个局部代码块，"
        "说明用户只想修改当前聚焦的代码。此时：只输出修改后的代码片段，不要输出全文，不要输出解释。"
        "如果没有选区，则以代码审查/架构分析的角度来理解和回应。"
    ),
    "browser": (
        "当前用户正在浏览器中浏览网页。用户提供的是网页文本内容。"
        "请以网页内容分析/信息提取的角度来理解和回应。"
    ),
    "drag": (
        "用户通过拖拽的方式提交了一段文本。该文本可能来自任意应用程序。"
    ),
    "chat": (
        "用户正在与ASU Copilot进行连续对话。请基于已有的对话历史进行连贯的追问回复。"
    ),
    "revision": (
        "用户正在对文档进行修订。你收到两部分：[selection] 是用户选中的待修改文本，"
        "[content] 是完整文档。请先按选中文本的要求进行修改，再扫描全文找出由于此修改而产生矛盾"
        "或也应同步调整的位置，标记给用户。"
    ),
    "ppt_generator": (
        "你现在是一个顶级的AI幻灯片策划师与结构化数据工程师。"
        "用户的意图是根据提供的 [content]（长文本或大纲）生成一份高质量的演示文稿（PPT）。\n"
        "你的任务是对文案进行降维提炼，并将结果严格输出为符合下列规范的 JSON 数组"
        "（不要输出任何 Markdown、不要输出任何解释说明代码，只输出 JSON）：\n"
        "[\n"
        "  {\n"
        '    "type": "title", // 封面页\n'
        '    "layout": "center", // title 页默认 center\n'
        '    "title": "主标题",\n'
        '    "subtitle": "副标题或日期"\n'
        "  },\n"
        "  {\n"
        '    "type": "content", // 内容页\n'
        '    "layout": "text_only", // 页面版式：text_only(纯文本), image_right(右侧配图), three_columns(三栏对比)\n'
        '    "title": "页面大标题",\n'
        '    "items": [\n'
        '      {"level": 0, "text": "一级要点"},\n'
        '      {"level": 1, "text": "二级说明"}\n'
        "    ]\n"
        "  }\n"
        "]\n"
        "要求：\n"
        "1. 必须对长篇大论进行提炼压缩，不要把长段落直接塞进 PPT。\n"
        "2. 页面不能过载，单页 items 超过 6 条时，请主动切分为新的一页（title后加'（续）'）。\n"
        "3. 智能选择版式：如果内容适合配图说明，设置 layout 为 'image_right'；"
        "如果是多项并列对比，设置 layout 为 'three_columns'；默认使用 'text_only'。"
    ),
    "ppt_editor": (
        "你是一个 PPT 编辑助手。优先进行局部修改，而不是重新生成整个PPT。\n\n"
        "修改模式（按优先级排序）：\n\n"
        "1. **局部修改**（推荐）：只修改用户指定的部分\n"
        '   - 修改标题：{"action": "update", "slide_index": 1, "field": "title", "value": "新标题"}\n'
        '   - 修改副标题：{"action": "update", "slide_index": 0, "field": "subtitle", "value": "新副标题"}\n'
        '   - 修改版式：{"action": "update", "slide_index": 0, "field": "layout", "value": "image_right"}\n\n'
        "2. **修改要点**：\n"
        '   - 更新要点：{"action": "update_item", "slide_index": 1, "item_index": 0, "field": "text", "value": "新内容"}\n'
        '   - 添加要点：{"action": "add_item", "slide_index": 1, "item": {"text": "新要点", "level": 0, "content_type": "text"}}\n'
        '   - 删除要点：{"action": "remove_item", "slide_index": 1, "item_index": 0}\n\n'
        "3. **幻灯片操作**：\n"
        '   - 添加幻灯片：{"action": "add_slide", "index": 2, "slide": {"title": "新页面", "type": "content", "layout": "text_only", "items": []}}\n'
        '   - 删除幻灯片：{"action": "remove_slide", "index": 2}\n\n'
        "4. **内容转换**（当用户要求转换为图表/表格/图片时）：\n\n"
        "   **重要：从非结构化内容中提取数据的技巧**\n\n"
        '   当用户说"把这个内容做成表格"或"用图表展示"时，你需要：\n'
        "   1. 分析内容结构，识别出可提取的数据模式\n"
        "   2. 从自然语言中提取关键信息（人物、属性、数值等）\n"
        "   3. 将提取的数据组织成表格/图表格式\n\n"
        "   **常见提取模式**：\n"
        "   - **人物属性**：张三25岁在北京 -> 列：[姓名, 年龄, 城市]\n"
        "   - **产品对比**：产品A卖100万，产品B卖200万 -> 列：[产品, 销量]\n"
        "   - **时间序列**：Q1增长10%，Q2增长15% -> 列：[季度, 增长率]\n"
        "   - **列表描述**：优点：便宜、快速、可靠 -> 列：[优点]\n\n"
        "   **转换指令格式**：\n\n"
        "   a) 转为表格：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "标题", "columns": ["列1", "列2"], "rows": [["值1", "值2"]]}}}\n\n'
        "   b) 转为柱状图（适合对比）：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "标题", "labels": ["标签1", "标签2"], "datasets": [{"label": "系列", "data": [10, 20], "color": "#007bff"}]}}}\n\n'
        "   c) 转为折线图（适合趋势）：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "line", "chart_data": {...}}}\n\n'
        "   d) 转为饼图（适合占比）：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "pie", "chart_data": {...}}}\n\n'
        "   e) 转为流程图（适合步骤）：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "flowchart", "flowchart_data": {"title": "标题", "steps": ["步骤1", "步骤2"]}}}\n\n'
        "   f) 添加图片（使用占位符或描述）：\n"
        '   {"action": "add_item", "slide_index": 0, "item": {"content_type": "image", "image_url": "描述或URL"}}\n\n'
        '5. **全局修改**（仅当用户明确要求"重新生成"时使用）：\n'
        '   - 返回 {"slides": [...]}\n\n'
        "内容类型：text / image / flowchart / icon / table / chart\n"
        "版式类型：center / text_only / image_right / image_left / three_columns / two_columns / full_image"
    ),
}


# ==========================================
# Context Source 优先级与冲突清理
# ==========================================

# context_source 与 action_type 的优先级映射
# 当 context_source 具有明确的行为指令时，应覆盖 persona 的通用指令
CONTEXT_SOURCE_PRIORITY = {
    "ide": "high",        # IDE 上下文有明确的行为指令（只输出修改后的代码）
    "revision": "high",   # 修订模式有明确的输出格式要求
    "ppt_generator": "high",  # PPT 生成有明确的 JSON 输出要求
    "ppt_editor": "high",     # PPT 编辑有明确的 JSON 输出要求
    "browser": "medium",  # 浏览器上下文有行为倾向
    "chat": "low",        # 聊天模式主要依赖 persona
    "drag": "low",        # 拖拽模式主要依赖 persona
}

# 当 context_source 优先级高于 persona 时，应从 persona 中移除的关键词/指令
# 避免与 context_source 指令冲突
PERSONA_CONFLICT_PATTERNS = {
    "ide": [
        "简要解释", "深度解析", "总结核心功能", "指出潜在漏洞",  # 与"不要输出解释"冲突
        "翻译为中文", "翻译为英文",  # 与"只输出修改后的代码"冲突
    ],
    "revision": [
        "只输出修改后的文本", "不要输出任何解释",  # 与修订的"三个独立区块"冲突
    ],
    "ppt_generator": [
        "翻译", "解释", "总结", "润色",  # 与"生成 PPT JSON"冲突
    ],
    "ppt_editor": [
        "翻译", "解释", "总结", "润色",  # 与"编辑 PPT JSON"冲突
    ],
}


# ==========================================
# Persona 加载
# ==========================================

def load_persona(persona_name: str, base_dir: str = None) -> str:
    """
    动态加载 Persona 文件，支持热更新
    
    Args:
        persona_name: persona 名称（如 "default", "code", "translate", "chat"）
        base_dir: personas 目录路径，默认为项目根目录下的 personas/
    
    Returns:
        persona 内容字符串
    """
    if base_dir is None:
        # 向上导航到项目根目录（opencopilot/shared/ -> opencopilot/ -> 项目根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        base_dir = os.path.join(project_root, "personas")
    
    filepath = os.path.join(base_dir, f"{persona_name}.md")
    if not os.path.exists(filepath):
        # 回退到默认 persona
        filepath = os.path.join(base_dir, "default.md")
        if not os.path.exists(filepath):
            return "你是一个强大的AI助手，请直接回答用户的问题。"
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


# ==========================================
# Context Prefix 构建
# ==========================================

def build_context_prefix(context_source: str, context_meta: Dict[str, Any] = None) -> str:
    """
    根据上下文来源和元信息，生成注入到 system prompt 的前缀描述。
    
    Args:
        context_source: 上下文来源类型（如 "ide", "browser", "ppt_editor" 等）
        context_meta: 上下文元信息字典
    
    Returns:
        context prefix 字符串
    """
    base = CONTEXT_DESCRIPTIONS.get(context_source, "")
    parts = [base] if base else []

    if context_meta:
        file_name = context_meta.get("file_name", "")
        language = context_meta.get("language", "")
        app_name = context_meta.get("app_name", "")
        task = context_meta.get("task", "")
        revision_target = context_meta.get("revision_target", "")
        custom_instruction = context_meta.get("custom_instruction", "")
        source_text = context_meta.get("source_text", "")

        if context_source in ("ide", "revision") and file_name:
            detail = f"文件名：{file_name}"
            if language:
                detail += f"，编程语言：{language}"
            parts.append(detail)
        elif context_source == "browser" and app_name:
            parts.append(f"浏览器：{app_name}")

        # 全局系统焦点和最近使用历史（如果存在）
        current_app = context_meta.get("current_active_app")
        recent_apps = context_meta.get("recent_apps", [])
        if current_app or recent_apps:
            sys_state = "【全局系统状态】\n"
            if current_app:
                sys_state += f"- 当前用户正在使用的前台软件是: {current_app}\n"
            if recent_apps:
                sys_state += f"- 用户最近切换过的软件历史: {', '.join(recent_apps)}\n"
            sys_state += "(如果用户询问当前在使用什么软件或开启了哪些程序，请参考上述信息回答)"
            parts.append(sys_state)

        # 任务上下文：工作台设定的任务注入到所有请求中
        if task:
            parts.append(f"用户当前任务：{task}。请围绕此任务目标进行回答，将分析结果与任务关联。")

        # 修订模式降级：无全文时告知 Agent 仅做局部修订
        if revision_target and context_source == "revision":
            parts.append(f"[选择文本]（待修订内容）:\n{revision_target}")

        # 自定义指令：明确告诉 Agent 用户的修改要求
        if custom_instruction:
            parts.append(f"[用户修改指令] {custom_instruction}\n请严格按此指令对提供的文本进行修改，只输出修改后的结果，不要输出任何解释。")

        # 聊天模式中附带的源文本上下文
        if source_text and context_source == "chat":
            preview = source_text[:2000] + ("…" if len(source_text) > 2000 else "")
            parts.append(f"[用户当前关注的源文本]:\n{preview}")

    return "\n".join(parts)


# ==========================================
# Persona 冲突清理
# ==========================================

def sanitize_persona_for_context(persona_prompt: str, context_source: str) -> str:
    """
    根据 context_source 的优先级，清理 persona 中可能冲突的指令。
    
    当 context_source 具有高优先级时，移除 persona 中可能与之冲突的指令，
    避免 system prompt 中出现重复或矛盾的指令。
    
    Args:
        persona_prompt: 原始 persona 内容
        context_source: 上下文来源类型
    
    Returns:
        清理后的 persona 内容
    """
    priority = CONTEXT_SOURCE_PRIORITY.get(context_source, "low")
    
    # 低优先级：不修改 persona
    if priority == "low":
        return persona_prompt
    
    # 获取需要移除的冲突模式
    conflict_patterns = PERSONA_CONFLICT_PATTERNS.get(context_source, [])
    if not conflict_patterns:
        return persona_prompt
    
    # 检查 persona 是否包含冲突模式
    persona_lower = persona_prompt.lower()
    has_conflict = any(pattern in persona_lower for pattern in conflict_patterns)
    
    if not has_conflict:
        return persona_prompt
    
    # 对于高优先级 context_source，添加明确的优先级说明
    priority_note = f"\n\n【重要】当前上下文（{context_source}）的行为指令优先于上述人设指令。请优先遵循上下文指令。"
    
    return persona_prompt + priority_note


# ==========================================
# 统一 Prompt 构建入口
# ==========================================

def build_full_prompt(
    action_type: str,
    context_source: str,
    context_content: str,
    context_meta: Dict[str, Any] = None,
    persona_name: str = None,
) -> str:
    """
    统一的 prompt 构建入口
    
    所有模块应通过此函数构建最终的 prompt，确保：
    - persona 加载统一
    - context_source 处理统一
    - persona/context 冲突清理统一
    
    Args:
        action_type: 动作类型（如 "chat", "translate", "code" 等）
        context_source: 上下文来源（如 "ide", "browser", "ppt_editor" 等）
        context_content: 用户输入内容
        context_meta: 上下文元信息
        persona_name: persona 名称，默认使用 action_type
    
    Returns:
        完整的 prompt 字符串
    """
    # 1. 加载 persona
    persona_name = persona_name or action_type
    persona = load_persona(persona_name)
    
    # 2. 构建 context prefix
    context_prefix = build_context_prefix(context_source, context_meta or {})
    
    # 3. 清理 persona 冲突
    persona = sanitize_persona_for_context(persona, context_source)
    
    # 4. 组装
    parts = []
    if context_prefix:
        parts.append(context_prefix)
    parts.append(persona)
    parts.append(f"\n\n用户请求：{context_content}")
    
    return "\n".join(parts)


def build_system_messages(
    action_type: str,
    context_source: str,
    context_content: str,
    context_meta: Dict[str, Any] = None,
    persona_name: str = None,
) -> list:
    """
    构建 system messages 列表（用于支持多轮对话的 API）
    
    Returns:
        [{"role": "system", "content": "..."}] 格式的消息列表
    """
    prompt = build_full_prompt(
        action_type=action_type,
        context_source=context_source,
        context_content=context_content,
        context_meta=context_meta,
        persona_name=persona_name,
    )
    return [{"role": "system", "content": prompt}]
