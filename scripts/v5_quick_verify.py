"""V5 快速验证脚本 - 测试核心修复"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("  V5 核心修复快速验证")
print("=" * 60)

passed = 0
total = 0

def check(label, cond, detail=""):
    global passed, total
    total += 1
    icon = "PASS" if cond else "FAIL"
    if cond:
        passed += 1
    msg = f"  [{icon}] {label}"
    if detail:
        msg += f"  -- {detail}"
    print(msg)
    return cond

# ============ 测试 1: Persona ============
print("\n--- 测试1: Persona 加载 ---")
from opencopilot.shared.prompt import load_persona
ppt = load_persona("ppt")
default = load_persona("default")
print(f"  ppt.md: {len(ppt)} chars, default.md: {len(default)} chars")
check("ppt.md 存在且 >500", len(ppt) > 500, f"实际: {len(ppt)}")
check("ppt 含 JSON", "JSON" in ppt or "json" in ppt.lower())
check("ppt 含 slides", "slides" in ppt)
check("ppt != default", ppt != default)

# ============ 测试 2: Context Source ============
print("\n--- 测试2: Context Source 前缀 ---")
from opencopilot.shared.prompt import build_context_prefix, CONTEXT_DESCRIPTIONS
check("studio in CONTEXT_DESCRIPTIONS", "studio" in CONTEXT_DESCRIPTIONS)
pfx = build_context_prefix("studio", {})
check("studio 前缀非空", len(pfx) > 0, f"前缀: {pfx}")

# ============ 测试 3: ImmuneSystem ============
print("\n--- 测试3: ImmuneSystem 误拦截修复 ---")
from opencopilot.safety.immune import ImmuneSystem, RuleContext
immune = ImmuneSystem()
doc = '配置示例：api_key = "sk-test-123" token = "abc123" password = "admin"'

async def test_immune():
    # 默认 action
    ctx1 = RuleContext(session_id="test")
    r1 = await immune.check_content(ctx1, doc)
    print(f"  默认action: allowed={r1.allowed}, msg={r1.message}")
    check("默认action: 含代码文档被 BLOCK", not r1.allowed)

    # PPT action
    ctx2 = RuleContext(session_id="test")
    ctx2.current_action = "content_generation:ppt"
    r2 = await immune.check_content(ctx2, doc)
    print(f"  PPT action:  allowed={r2.allowed}, msg={r2.message}")
    check("PPT action: 含代码文档被 ALLOW (修复验证)", r2.allowed)

    # 翻译 action
    ctx3 = RuleContext(session_id="test")
    ctx3.current_action = "content_generation:translate"
    r3 = await immune.check_content(ctx3, doc)
    check("Translate action: 含代码文档被 ALLOW", r3.allowed)

    # 危险命令 (即使 PPT 也应拦截 constraint 类型)
    ctx4 = RuleContext(session_id="test")
    ctx4.current_action = "content_generation:ppt"
    r4 = await immune.check_content(ctx4, "rm -rf /")
    print(f"  危险命令:  allowed={r4.allowed}, msg={r4.message}")
    check("PPT action: 危险 Shell 命令仍被 BLOCK", not r4.allowed)

asyncio.run(test_immune())

# ============ 测试 4: Prompt 构建 ============
print("\n--- 测试4: Prompt 完整构建 ---")
from opencopilot.shared.prompt import build_full_prompt
prompt = build_full_prompt(
    action_type="ppt", context_source="studio",
    context_content="请根据预算报告生成PPT大纲",
    context_meta={}, persona_name="ppt"
)
check("完整 prompt > 500", len(prompt) > 500, f"实际: {len(prompt)}")
check("包含 Studio 上下文", "Studio" in prompt or "工作台" in prompt)
check("包含 slides 字段", "slides" in prompt)
check("包含用户请求", "预算报告" in prompt)

# ============ 测试 5: JSON 解析 ============
print("\n--- 测试5: JSON 解析 ---")
from gui.v5.studio_tab import StudioTabV5
import json

std = json.dumps({"title": "测试", "slides": [
    {"type": "title", "layout": "center", "title": "封面", "subtitle": "副标题"},
    {"type": "content", "layout": "text_only", "title": "内容", "items": [{"level": 0, "text": "要点1"}]}
]}, ensure_ascii=False)

s1 = StudioTabV5._parse_slides_from_text(std)
check("标准 JSON", len(s1) == 2, f"实际: {len(s1)}")

md = f"说明文字\n```json\n{std}\n```\n结尾"
s2 = StudioTabV5._parse_slides_from_text(md)
check("Markdown 包裹", len(s2) == 2, f"实际: {len(s2)}")

s3 = StudioTabV5._parse_slides_from_text("无法生成PPT")
check("无效文本返回空", len(s3) == 0)

# ============ 汇总 ============
print(f"\n{'='*60}")
print(f"  结果: {passed}/{total} 通过")
if passed == total:
    print("  全部通过!")
else:
    print(f"  有 {total - passed} 项未通过")
print(f"{'='*60}")
