"""
Skill 体系集成测试

全链路验证：
1. SkillLoader 扫描 SKILL.md → 解析 YAML frontmatter → 生成工具描述
2. SkillRegistry 注册所有 Skill（含 ContentConvertSkill）
3. SessionSetupMiddleware._get_tools_prompt() 注入工具描述到 enriched_system
4. 工具描述内容完整性校验（参数、描述、工具名均出现在 System Prompt 中）

不依赖 LLM，不 mock 任何外部调用。
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSkillLoaderDiscovery:
    """SkillLoader 扫描与解析验证"""

    def test_skill_loader_finds_content_convert(self):
        """SkillLoader 应扫描到 content_convert SKILL.md"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        all_skills = loader.load_all()
        names = [s.name for s in all_skills]

        assert "content_convert" in names, (
            f"content_convert 未被扫描到，已发现: {names}"
        )

    def test_content_convert_has_4_tools(self):
        """content_convert 应声明 4 个工具"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        loader.load_all()
        spec = loader.skills.get("content_convert")

        assert spec is not None, "content_convert spec 不存在"
        tool_names = [t.name for t in spec.tools]
        assert len(tool_names) == 4, f"期望 4 个工具，实际: {tool_names}"
        assert "analyze_and_convert" in tool_names
        assert "convert_to_table" in tool_names
        assert "convert_to_chart" in tool_names
        assert "convert_to_flowchart" in tool_names

    def test_content_convert_tool_parameters(self):
        """工具参数声明完整性"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        loader.load_all()
        spec = loader.skills["content_convert"]

        # analyze_and_convert 应有 text + title 参数
        analyze_tool = next(t for t in spec.tools if t.name == "analyze_and_convert")
        assert "text" in analyze_tool.parameters, "analyze_and_convert 缺少 text 参数"
        assert analyze_tool.parameters["text"].get("required") is True

        # convert_to_chart 应有 chart_type 参数
        chart_tool = next(t for t in spec.tools if t.name == "convert_to_chart")
        assert "chart_type" in chart_tool.parameters, "convert_to_chart 缺少 chart_type 参数"

    def test_content_convert_eligibility(self):
        """content_convert 应通过 Eligibility 检查"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        eligible = loader.load_eligible()
        eligible_names = [s.name for s in eligible]

        assert "content_convert" in eligible_names, (
            f"content_convert 未通过 Eligibility，eligible: {eligible_names}"
        )


class TestSkillRegistry:
    """SkillRegistry 注册验证"""

    def test_content_convert_registered(self):
        """ContentConvertSkill 应被注册到 SkillRegistry"""
        from opencopilot.capabilities.skill import SkillRegistry

        registry = SkillRegistry()
        assert "content_convert" in registry._skills, (
            f"content_convert 未注册，已注册: {list(registry._skills.keys())}"
        )

    def test_content_convert_metadata(self):
        """ContentConvertSkill 元数据完整性"""
        from opencopilot.capabilities.skill import ContentConvertSkill

        skill = ContentConvertSkill()
        meta = skill.metadata

        assert meta.name == "content_convert"
        assert meta.version == "1.0.0"
        assert len(meta.intents) >= 4, f"intents 不足: {meta.intents}"
        assert "analyze_and_convert" in meta.intents
        assert "convert_to_table" in meta.intents
        assert "convert_to_chart" in meta.intents
        assert "convert_to_flowchart" in meta.intents

    def test_content_convert_can_handle(self):
        """can_handle 置信度验证"""
        import asyncio
        from opencopilot.capabilities.skill import ContentConvertSkill
        from opencopilot.capabilities.skill.models import SkillContext

        skill = ContentConvertSkill()

        # 精确意图匹配 → 0.95
        ctx1 = SkillContext(intent="content_convert", input_data={"text": "test"})
        score1 = asyncio.run(skill.can_handle(ctx1))
        assert score1 >= 0.9, f"精确意图匹配置信度不足: {score1}"

        # 关键词匹配 → 0.8
        ctx2 = SkillContext(intent="chat", input_data={"text": "帮我把这个转成表格"})
        score2 = asyncio.run(skill.can_handle(ctx2))
        assert score2 >= 0.7, f"关键词匹配置信度不足: {score2}"

        # 无关请求 → 0.0
        ctx3 = SkillContext(intent="chat", input_data={"text": "你好"})
        score3 = asyncio.run(skill.can_handle(ctx3))
        assert score3 == 0.0, f"无关请求应返回 0.0: {score3}"


class TestSystemPromptInjection:
    """System Prompt 工具描述注入验证"""

    def test_build_tools_prompt_contains_all_tools(self):
        """build_tools_prompt 生成的描述应包含所有 content_convert 工具"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        eligible = loader.load_eligible()
        tools_prompt = loader.build_tools_prompt(eligible)

        assert len(tools_prompt) > 0, "工具描述为空"
        assert "content_convert" in tools_prompt, "工具描述中无 content_convert"
        assert "analyze_and_convert" in tools_prompt
        assert "convert_to_table" in tools_prompt
        assert "convert_to_chart" in tools_prompt
        assert "convert_to_flowchart" in tools_prompt

    def test_tools_prompt_contains_parameter_descriptions(self):
        """工具描述应包含参数信息"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        eligible = loader.load_eligible()
        tools_prompt = loader.build_tools_prompt(eligible)

        # 验证参数类型和描述出现
        assert "text" in tools_prompt, "工具描述中缺少 text 参数"
        assert "chart_type" in tools_prompt, "工具描述中缺少 chart_type 参数"

    def test_session_setup_get_tools_prompt(self):
        """SessionSetupMiddleware._get_tools_prompt() 应返回非空工具描述"""
        from opencopilot.agent.middlewares import SessionSetupMiddleware

        # 构造最小化 middleware 实例
        middleware = SessionSetupMiddleware(
            memory=None,
            window_manager=None,
            normalize_context_envelope=None,
            load_persona=None,
            build_context_prefix=None,
            sanitize_persona_for_context=None,
        )

        tools_prompt = middleware._get_tools_prompt()
        assert tools_prompt is not None, "_get_tools_prompt 返回 None"
        assert len(tools_prompt) > 100, f"工具描述过短: {len(tools_prompt)} chars"
        assert "content_convert" in tools_prompt

        # 验证缓存机制：第二次调用应返回相同结果
        tools_prompt_2 = middleware._get_tools_prompt()
        assert tools_prompt == tools_prompt_2, "缓存机制异常：两次调用结果不同"


class TestAllSkillsLoadable:
    """所有 Skill 均可正常加载和实例化"""

    def test_all_skill_md_parseable(self):
        """所有 SKILL.md 文件可被正确解析"""
        from opencopilot.agent.skill_loader import SkillLoader

        loader = SkillLoader(skills_dir="skills/")
        all_skills = loader.load_all()

        assert len(all_skills) >= 4, f"应至少发现 4 个 Skill，实际: {len(all_skills)}"
        for spec in all_skills:
            assert spec.name, f"Skill 名称为空: {spec}"
            assert spec.description, f"Skill {spec.name} 描述为空"
            assert len(spec.tools) > 0, f"Skill {spec.name} 无工具声明"

    def test_all_builtin_skills_registered(self):
        """所有内置 Skill 类均可注册（无导入异常）"""
        from opencopilot.capabilities.skill import SkillRegistry

        registry = SkillRegistry()
        registered = list(registry._skills.keys())

        # 至少包含已知的内置 Skill
        expected = ["content_convert"]
        for name in expected:
            assert name in registered, f"{name} 未注册，已注册: {registered}"
