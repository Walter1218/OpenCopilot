"""
声明式 Skill 加载器

解析 SKILL.md 文件（YAML frontmatter + Markdown body），
支持 Eligibility 门控（OS/环境/Python 版本检查），
自动生成 LLM System Prompt 中的工具描述。

使用方式:
    loader = SkillLoader(skills_dir="skills/")
    skills = loader.load_all()
    for skill in skills:
        if skill.is_eligible():
            registry.register(skill)
"""

import os
import re
import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path

from .types import SkillSpec, ToolSpec


class SkillLoader:
    """SKILL.md 文件加载器

    职责：
    1. 扫描 skills/ 目录发现所有 SKILL.md
    2. 解析 YAML frontmatter 提取元数据和工具声明
    3. 执行 Eligibility 门控检查
    4. 生成工具描述文本（注入 System Prompt）
    """

    def __init__(self, skills_dir: str = "skills/"):
        self._skills_dir = Path(skills_dir)
        self._skills: Dict[str, SkillSpec] = {}

    @property
    def skills(self) -> Dict[str, SkillSpec]:
        return self._skills

    def load_all(self) -> List[SkillSpec]:
        """扫描并加载所有 SKILL.md 文件"""
        loaded = []
        if not self._skills_dir.exists():
            print(f"[SkillLoader] Skills directory not found: {self._skills_dir}")
            return loaded

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                spec = self._parse_skill(skill_md)
                if spec:
                    self._skills[spec.name] = spec
                    loaded.append(spec)
                    eligible = "✓" if spec.is_eligible() else "✗"
                    print(f"[SkillLoader] {eligible} {spec.name} ({len(spec.tools)} tools)")
            except Exception as e:
                print(f"[SkillLoader] Failed to load {skill_md}: {e}")

        return loaded

    def load_eligible(self) -> List[SkillSpec]:
        """只加载满足 Eligibility 条件的 Skill"""
        return [s for s in self.load_all() if s.is_eligible()]

    def _parse_skill(self, filepath: Path) -> Optional[SkillSpec]:
        """解析单个 SKILL.md 文件"""
        content = filepath.read_text(encoding="utf-8")

        # 提取 YAML frontmatter (--- 包裹)
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
        if not fm_match:
            print(f"[SkillLoader] No frontmatter found in {filepath}")
            return None

        frontmatter_str = fm_match.group(1)
        markdown_body = fm_match.group(2).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            print(f"[SkillLoader] YAML parse error in {filepath}: {e}")
            return None

        if not isinstance(frontmatter, dict):
            return None

        # 解析工具声明
        tools = []
        for tool_data in frontmatter.get("tools", []):
            if isinstance(tool_data, dict):
                tools.append(ToolSpec(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                ))

        return SkillSpec(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            eligibility=frontmatter.get("eligibility", {}),
            tools=tools,
            markdown_body=markdown_body,
            source_file=str(filepath),
        )

    def build_tools_prompt(self, skills: List[SkillSpec] = None) -> str:
        """生成工具描述文本（注入 System Prompt）

        格式遵循 OpenAI Function Calling 标准，LLM 可根据描述自主决定调用。
        """
        if skills is None:
            skills = list(self._skills.values())

        if not skills:
            return ""

        lines = ["# 可用工具\n"]
        for skill in skills:
            if not skill.is_eligible():
                continue
            lines.append(f"## {skill.name}")
            lines.append(f"{skill.description}\n")
            for tool in skill.tools:
                params_str = ""
                for pname, pdef in tool.parameters.items():
                    if isinstance(pdef, dict):
                        required = " (必需)" if pdef.get("required") else ""
                        default = f", 默认: {pdef.get('default')}" if pdef.get("default") is not None else ""
                        params_str += f"\n    - {pname}: {pdef.get('type', 'string')}{required}{default} - {pdef.get('description', '')}"
                lines.append(f"- **{tool.name}**: {tool.description}{params_str}")

        return "\n".join(lines)

    def get_tool(self, tool_name: str) -> Optional[ToolSpec]:
        """按名称查找工具声明"""
        for skill in self._skills.values():
            for tool in skill.tools:
                if tool.name == tool_name:
                    return tool
        return None

    def get_skill_names(self) -> List[str]:
        """获取所有已加载的 Skill 名称"""
        return list(self._skills.keys())
