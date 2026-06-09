# OpenCopilot 🚀

> **The macOS System-Level AI Right-Click Menu** — Select text anywhere, double right-click, AI appears.
>
> Not an IDE plugin · Not a chat window · Not an autonomous agent · The shortest path between you and AI

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%2012%2B-blue" alt="platform">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-green" alt="python">
  <img src="https://img.shields.io/badge/version-v5.0-orange" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="license">
  <a href="README_CN.md">中文</a>
</p>

---

## Positioning: The Shortest Path Between You and AI

### The Current AI Assistant Landscape

As of 2025-2026, desktop AI tools have split into four lanes:

| Lane | Examples | Model | Limitation |
|------|----------|-------|------------|
| **IDE-Embedded** | Cursor / Trae / Windsurf / Copilot | AI inside the editor, Tab completion + Chat panel | Dead outside the IDE; useless for emails, PPTs, web browsing |
| **Standalone Chat** | Claude Desktop / ChatGPT Desktop | Independent app + file/MCP access | Powerful tools, but you must "feed" content to them — copy-paste or upload |
| **Desktop Office Agent** | WorkBuddy / QoderWork / DuMate | AI operates your desktop, generates Word/PPT/Excel | Fast first-draft generation, but riddled with hallucinations — fabricated numbers, broken formatting, logical gaps |
| **Autonomous Desktop Agent** | OpenClaw / Hermes / Solo | AI takes over the desktop, fully autonomous | Powerful but opaque; you can't intervene when it goes wrong; security risk |

### OpenCopilot's Fifth Lane: System-Level On-Demand Review & Fix

OpenCopilot takes none of these paths. Its design philosophy: **AI is an extension of your right mouse button, not another window.** And its killer use case: **when WorkBuddy generates a hallucination-filled draft, OpenCopilot helps you find and fix every problem — without leaving Office.**

```
Cursor / Trae:
  You → switch to IDE → ask a question → wait → manually apply result
  Coverage: ████████░░  IDE only

Claude Desktop:
  You → ⌘Tab to Claude → type description → ⌘C⌘V content → wait → ⌘C⌘V result → ⌘Tab back
  Coverage: ████████████ Any app, but you shuttle content

WorkBuddy / QoderWork:
  AI → generates full PPT/doc → you open it → spot a hallucination → ???
  Coverage: ████████████ Fast draft, but you're stuck reviewing alone

OpenClaw / Hermes:
  AI → operates desktop autonomously → you watch
  Coverage: ████████████ Any app, but you're a passenger

OpenCopilot:
  WorkBuddy outputs a draft → you open in Office → select suspicious content → double right-click → AI reviews & fixes it
  Coverage: ████████████ Any app, you review while AI fixes
```

**In one sentence**:
- Cursor asks "what code do you want to write" — **you're in the IDE**
- Claude Desktop asks "paste your content here" — **you're in a chat window**
- WorkBuddy says "here's your draft" — **you're stuck reviewing hallucinations alone**
- OpenClaw says "I'll handle it" — **you're in the passenger seat**
- OpenCopilot — WorkBuddy generates, you review, OpenCopilot fixes — **AI drafts, you steer**

### The Office AI Era: They Generate, You Review & Fix

The 2026 office AI landscape makes one thing clear: **WorkBuddy / QoderWork / DuMate have matured at "rapid first-draft generation"** — type one sentence, get a PPT/document in 3-10 minutes. The problem is:

> AI-generated drafts are riddled with hallucinations — fabricated numbers, invented citations, logical contradictions, formatting chaos. You need a tool to **review and fix** the draft, not to generate yet another one.

This is exactly where OpenCopilot sits:

```
Traditional workflow:
  WorkBuddy outputs a draft → you manually review page by page in Office → spot a suspicious number → ???

OpenCopilot workflow:
  WorkBuddy outputs a draft → open in Office for review
    → See "Q2 Revenue ¥38M" → select it → double right-click → "Does this match the Excel data?"
    → See a logical gap → select it → double right-click → "Check if this contradicts page 3"
    → Unprofessional phrasing → select it → double right-click → "Polish, B2B formal tone"
```

**4 Review Superpowers**:

| Superpower | Details |
|------------|---------|
| **In-Office Review** | Select and analyze directly in Word/WPS/PPT — no window switching |
| **Cross-Validation with Real Data** | Reads your Excel/docs as ground truth for comparison — not relying on LLM memory |
| **Pipeline Multi-Layer Review** | ImmuneSystem blocks dangerous output + CapabilityRouter classifies review type (data check / fact check / style check) |
| **Incremental Edit, Preserve Formatting** | Only changes the text you selected — never touches python-pptx generated layout |

### Why System-Level Intervention

OpenCopilot uses macOS **AXUIElement API** (Accessibility) to perceive your actions at the OS level, without depending on any specific app's plugin or API:

- Text selection → system-level event monitoring, no ⌘C needed
- Browser content → AppleScript bridge, no extension
- IDE full file → companion plugin (optional), not mandatory
- Screenshot analysis → CGWindow API, no app support required

This means OpenCopilot delivers the **exact same interaction experience** across **Word, PPT, browsers, email, terminal, Finder, and any text editor**. You're not using an "AI coding tool" or an "AI chat tool" — you're using an "AI right-click menu that works in any software."

---

## Interaction Design

### Three Interaction Postures

| Posture | Trigger | Intent | Form |
|---------|---------|--------|------|
| **Instant Advisor** | Double right-click | "Take a look at this for me" | Lightweight floating window, appears near the cursor, never steals focus |
| **Deep Workbench** | Triple right-click | "I have a complex task" | Independent workspace window, with task context + multi-turn dialogue |
| **Drag & Drop Feed** | Select → drag into card | "Fix just this part" | Accepts text dragged from any application |

**Core interaction principles**:

- **Never steals focus**: the floating window appears without interrupting your typing
- **Eyes stay put**: the floating window appears near the trigger point, no forced gaze shift
- **Context auto-carried**: selected text is automatically injected — no need to explain "the paragraph above"
- **Human in the loop, always**: every interaction triggered by you, every result confirmed by you — not a black-box agent, but your enhanced "smart right-click"

### v5.0 Interaction Upgrade

**Smart Copilot 3-Tab Architecture**:

| Tab | Function | Design Philosophy |
|-----|----------|-------------------|
| **Work** | Quick operations (Explain/Fix/Polish) | Primary/Secondary button hierarchy, Context Strip data source switching |
| **Chat** | Continuous dialogue | Context Panel shows available context sources, Skill Panel integrated at bottom |
| **Studio** | PPT co-creation workbench | Merges original Tab 3 + Tab 5, directly opens 4-Panel editor |

**Agent Workspace 2.0**:

| Panel | Function | Description |
|-------|----------|-------------|
| **Task** | Task definition & management | Task details + history + template loading |
| **Chat** | Session list + dialogue | Multi-session switching + persistence |
| **Files** | Recent files + drop zone | File management + context injection |
| **Memory** | Knowledge & context | Knowledge graph + translation memory + terminology |
| **Settings** | Engine / Theme / Shortcuts / Persona | Unified settings entry |

**Unified Settings Dialog**:

- 4 sections: Engine / Appearance / Shortcuts / Advanced
- 3 entry points: Smart Copilot Header / Workspace Sidebar / System Tray
- Replaces original 2 separate settings dialogs

### v5.0 Delivery Status

The v5 redesign is **partially shipped in code, not fully feature-complete**. Current repo status:

| Area | Already implemented in code | Still in progress |
|------|-----------------------------|-------------------|
| **Navigation** | `NavigationManager` centralizes Smart Copilot / Workspace / Studio / Settings lifecycle | More legacy windows still coexist in compatibility paths |
| **Smart Copilot** | 3-Tab shell (`Work / Chat / Studio`), drag & drop sharing, runtime-routed AI calls via `V5AgentWorker` | Further polish on markdown rendering, command palette, richer context chips |
| **Work / Chat** | Core interaction loop is usable: context fetch, streaming AI output, session handling, cancel, context chips, send-to-Studio and action telemetry | Richer result rendering, command palette, deeper session references |
| **Studio** | PPT co-creation is fully implemented: 4-Panel workbench, thumbnail strip, diff preview edit, AI chat flow, unified undo stack, export & fullscreen | ✅ Fully Implemented |
| **Workspace** | Sidebar + 5-panel shell, real AI connected in `Workspace Chat`, Task templates/imports, recent file preview/actions, memory summaries, settings summaries and bridge-backed operations | Deeper file management and richer knowledge browser remain future polish |
| **Settings** | Unified settings dialog with Engine / Appearance / Shortcuts / Advanced, bridge persistence and Workspace summary cards | More validation and broader config coverage |

### Current Acceptance Baseline

The main `V5 UI` AI paths have already passed production-grade functional validation:

- Real AI connected: `Work Tab` primary actions, `Chat Tab` core dialogue, `Workspace Chat`, `Studio Tab`, and in-editor `Studio Window` co-creation
- Not connected to real AI yet are mostly workflow surfaces or not-yet-shipped design items: `Workspace Files/Memory/Settings/Task`, `Work More`, `Skill Panel`, `Cmd+K`, and context-aware right-click skill menu
- Full UI/AI regression baseline: `427 passed`
- Real production validation: `27/27 PASS`

The quality gate now has a documented quantitative baseline:

- Score structure: `Reliability 30 + Quality 40 + UX 20 + Safety 10`
- Hard gates: `protocol_error_rate = 0`, `json_parse_failure_rate = 0`, `think_leak_rate = 0`
- Suggested release gate: overall `>= 4.3/5.0`, and `Explain / Code Review / PPT >= 4.5/5.0`

See `docs/CURRENT_UI_AI_ACCEPTANCE_20260609.md` for the full acceptance matrix and scorecard.

---

## Core Capabilities

### 🎯 Smart Analysis (Auto)

Select any content, AI automatically identifies the type and delivers analysis.

- Select code → architect-level review (design patterns, complexity, improvement suggestions)
- Select news → extract key points, analyze context
- Select data tables → data interpretation, trend analysis
- Not sure which action to pick? Tap ✨ Auto

### 🌐 Smart Translation

Select text → double right-click → 🌐 Translate. Supports 8 languages bidirectional (ZH/EN/JA/KO/FR/DE/ES/RU).

**Design highlight**: Translation direction is dynamically injected by the Pipeline's SessionSetup middleware into the System Prompt — ensuring the LLM accurately understands the target language, rather than guessing from a hardcoded "translate to English" instruction.

### 💻 Code Analysis

Not just syntax highlighting — **architect-level** code review:

- **Design pattern recognition**: auto-detect Factory, Strategy, Observer, etc.
- **Complexity analysis**: cyclomatic complexity, coupling assessment
- **Improvement suggestions**: performance bottlenecks, security risks, readability issues
- **Cross-reference revision**: when you modify one section, automatically scans the full file for places that need同步 adjustments

Works with the IDE companion extension for a closed loop: select code → AI modifies → write back to IDE.

### 📝 Document Cross-Reference Revision

When you modify a paragraph in a document, AI automatically scans the full text for contradictions.

**Three-part output**:
1. **Revised text**: your paragraph, fixed
2. **Cross-reference impact analysis**: other sections that need同步 updates (with line/paragraph references)
3. **Revision rationale**: logical basis for this change

Supports `.md`, `.txt`, `.py`, `.docx`, `.pptx`. Word/PPT files are auto-parsed to plain text via Privileged Broker for cross-scanning.

### 📊 PPT Co-Creation

The v5 codebase already includes a **fully implemented Studio PPT Co-creation Workbench**:

- Independent `StudioWindowV5` lifecycle managed by `NavigationManager`
- 4-region shell: `Source`, `Outline`, `Preview`, and bottom AI area
- Thumbnail strip with navigation support
- WYSIWYG preview and diff preview editing
- Advanced chart and native flowchart rendering support
- Natural language AI dialogue for slide modifications
- Unified Undo/Redo stack
- Full pipeline for text/slides loading, PPT export, and fullscreen preview

### 🔍 Multi-Source Context Awareness

OpenCopilot doesn't just "look up selected text" — it proactively fetches what you're looking at:

| Source | Trigger | What It Gets |
|--------|---------|-------------|
| Highlighted text (any app) | Double right-click (auto) | System-level AXUIElement silent read |
| IDE full file | Click 📥 Read Full File | Entire code file |
| Browser page | Click 🌐 Read Webpage | Full page content (Chrome/Safari/Brave/Edge/Arc) |
| Screenshot | Click 👁️ Visual Analysis | Foreground window screenshot → multimodal analysis |
| File selection | Click 📝 Full Revision | .docx / .pptx auto-parsed |

**You never need to tell AI "what I was looking at" — it already knows.**

### 🎭 Persona Workshop

Click the 🎭 icon on the card title bar to create custom AI roles. Each role is a Markdown file (stored in `personas/`), editable with instant effect:

```markdown
# Xiaohongshu Copywriter
You are a Xiaohongshu viral copywriting expert. Style requirements:
- Max 3 lines per paragraph
- Heavy emoji use ✨🔥💯
- Lots of exclamation marks and rhetorical questions
- End with 3-5 hashtag topics
```

### 💬 Continuous Dialogue

Click 💬 Continuous Dialogue for multi-turn mode. AI remembers the full conversation history, supporting gradual deep-dive analysis. With the Workbench's "Task Context" feature, all conversations share the same contextual anchor.

---

## Technical Architecture

### Design Decision: Pipeline Middleware vs Monolithic Prompt Stitching

Products like Cursor and Claude Desktop are essentially "chat window + capability plugins" — they gather context, stitch it into one giant prompt, and throw it at the LLM. The problems with this approach:

1. **Nowhere to put safety**: content filtering and permission checks embedded in prompts — LLM may bypass them
2. **Unobservable**: when something goes wrong, you can only see what the LLM output — not what happened in between
3. **Hard to extend**: adding a capability requires modifying prompt-stitching logic everywhere

OpenCopilot follows OpenClaw's approach with a **7-layer async Pipeline**. Each layer is an independent middleware — interceptable, observable, replaceable:

```
User Request
  │
  ▼
SessionSetup   ← session restore, persona load, translation direction dynamic injection
  │
  ▼
SecurityGuard  ← permission check, rate limiting (Lane Semaphore per-lane throttling)
  │
  ▼
ImmuneSystem   ← content safety detection, dangerous command filtering (independent of LLM)
  │
  ▼
Planner        ← task complexity assessment → Agent paradigm selection
  │
  ▼
StateTracking  ← session state tracking, checkpoint
  │
  ▼
CapabilityRouter ← capability routing (code execution / knowledge retrieval / search / LLM)
  │
  ▼
LLMAgent       ← Agent Loop hybrid paradigm
  │
  ├─ SIMPLE  → One-Shot (~2s): 80% of tasks
  ├─ MEDIUM  → Plan-and-Solve (~10s): multi-step tasks
  └─ COMPLEX → Plan+ReAct (~20s): tasks requiring error correction
```

**Key Pipeline capabilities**:

| Capability | Description |
|------------|-------------|
| **Short-circuit safety** | Security check fails → immediate rejection, LLM never sees dangerous content |
| **Full-chain observability** | 24 Timer instrumentation points classified by `action_type`, each layer's latency independently traceable |
| **Graceful cancellation** | User interrupt propagates via `CancelledError` through the async stack — no brutal truncation |
| **Declarative extension** | New capability = add one middleware, never touch existing code |

### Why Borrow from OpenClaw's Architecture?

OpenClaw's Pipeline + Agent Loop architecture solves three core problems in Agent engineering:

1. **Global persistent Event Loop**: not one thread per request — the whole process shares one `asyncio` loop; cancellation via `task.cancel()` not thread-killing
2. **Session-level serialization lock**: `asyncio.Lock` ensures only 1 Pipeline per session at a time — eliminating data races (the root cause of "repeated replies")
3. **Middleware hot-swap**: safety/routing/planning are independent — never touch the LLM prompt

**Key differences from OpenClaw**:

| | OpenClaw | OpenCopilot |
|---|---|---|
| Interaction model | Agent autonomous decision + tool calls | User-triggered + double right-click |
| Operation mode | Long-running autonomous tasks | Short interactions, on-demand intervention |
| Safety model | Tool permission whitelist | Pipeline multi-layer interception + ImmuneSystem |
| Capability focus | File/code/shell automation | Multi-app universal: Word/PPT/web/IDE/screenshot |
| Observability | Node.js ecosystem | Python + SQLite persistent logs + stderr real-time output |

**In short**: OpenClaw is "AI does the work for you", OpenCopilot is "AI lends a hand while you work". Both share the Pipeline architectural philosophy, but with different product visions.

**Current v5 UI integration note**:

- `Work`, `Chat`, and `Studio/PPT` all use the shared runtime entry in `gui/v5/agent_worker.py`
- `V5AgentWorker` now resolves `agent_runtime` dynamically: default route is `/vnext/* -> hermes_local`, while `self_agent`, capability overrides, and fallback policy are configurable
- non-AI UI actions go through `gui/v5/bridge.py`
- detailed runtime and startup behavior is maintained in `docs/STARTUP_GUIDE.md`

---

## Quick Start

### Requirements

- macOS 12+
- Python 3.11 ~ 3.13
- Terminal must be granted **Accessibility** and **Screen Recording** permissions (System Settings → Privacy & Security)

### Install

```bash
git clone https://github.com/Walter1218/OpenCopilot.git
cd OpenCopilot
pip install -e .
```

### Launch

```bash
# Terminal 1: Privileged Broker (:18889) - required for selection / active doc / apply-back
bash start_broker.sh

# Terminal 2: UI
bash scripts/start_ui.sh

# Optional: preheat vnext API manually if you want stable API logs
python3 -m uvicorn smart_copilot_api:app --host 127.0.0.1 --port 8010 --reload
```

For a more detailed startup matrix, see [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md).

After launch, the v5 UI is opened through `smart_copilot.py` → `gui/main.py`. Smart Copilot / Workspace / Studio are shown by the v5 navigation layer.

### Third-Party Agent Integration

The UI is now fixed as one `V5 UI`, and third-party agents are integrated through `Settings -> Engine -> Agent Runtime`:

- select `Third-Party Agent` in `Agent Mode`
- choose the current built-in third-party provider preset in `Agent Provider`
- configure `Agent Model`, which now propagates through `/vnext/tasks` into the Hermes run payload
- use `Capability Routes` to decide which capabilities stay on default routing vs. the third-party path
- use `Fallback Policy` to define automatic recovery when the third-party path fails

The current config-switchable third-party path still supports only `Hermes Local`; the same settings panel can switch between the self agent and the third-party path. Adding a new provider still requires updating the runtime adapter, the UI preset, tests, and documentation together. See `docs/STARTUP_GUIDE.md` and `docs/AGENT_RUNTIME_TARGET_ARCHITECTURE.md`.

---

## Project Structure

```
OpenCopilot/
├── opencopilot/                  # Main package
│   ├── agent/                    #   Agent core (Pipeline + Agent Loop + Caller)
│   │   ├── caller.py             #     Unified caller (sync/async), global Event Loop
│   │   ├── middlewares.py        #     7-layer Pipeline middleware
│   │   ├── pipeline.py           #     Pipeline engine + PipelineContext
│   │   ├── observability.py      #     Full-chain observability
│   │   └── log_store.py          #     SQLite persistent logging
│   ├── capabilities/             #   Capability layer
│   │   ├── coding/               #     Code execution engine
│   │   ├── knowledge/            #     Knowledge retrieval (Knowledge Graph)
│   │   ├── search/               #     Search engine
│   │   ├── memory/               #     Session memory management
│   │   ├── skill/                #     Declarative Skill system
│   │   ├── ppt/                  #     PPT co-creation engine
│   │   └── state/                #     State management (checkpoint/recovery)
│   ├── safety/                   #   Safety layer (security/immune)
│   ├── broker/                   #   System agent (AXUIElement silent selection/sandbox penetration)
│   ├── providers/                #   LLM providers
│   ├── observability/            #   Observability module
│   └── shared/                   #   Shared utilities (prompt building/context normalization)
├── api/                          # API Gateway / vnext API (8010 preferred, 8000 fallback)
│   ├── app.py                    #   Route factory
│   └── routers/                  #   16+ independent route modules
├── gui/                          # PyQt6 desktop app
│   ├── main.py                   #   Entry + CopilotManager
│   ├── v5/                       #   v5 interaction layer (Navigation / Work / Chat / Studio / Settings)
│   ├── window.py                 #   Legacy/compat floating card
│   ├── workspace.py              #   Legacy/compat workspace
│   ├── workers/                  #   QThread Workers
│   └── dialogs/                  #   Translation/Persona dialogs
├── widgets/                      # PyQt6 widgets (skill panel, settings dialog, etc.)
├── asu_custom_agent.py           # Legacy/compat Agent service entry (:18888), not required for current v5 mainline
├── asu_broker/                   # Privileged Broker service (:18889)
├── coding_agent/                 # Coding agent implementation
├── context_manager/              # Context management system
├── core/                         # Core utilities and managers
├── knowledge_graph/              # Knowledge graph implementation
├── docs/                         # Documentation
│   ├── UI_Redesign_Plan_v5.md    # v5.0 UI redesign plan
│   ├── PPT_CoCreation_Design.md  # PPT co-creation design
│   ├── PPT_CoCreation_Iteration_Plan.md # PPT iteration plan
│   ├── VNEXT_REBUILD_BLUEPRINT.md # vnext rebuild blueprint
│   ├── VNEXT_UNIFIED_AGENT_API.md # vnext unified agent API contract
│   ├── VNEXT_DOC_INDEX.md # vnext document index
│   ├── VNEXT_MODULE_BOUNDARIES.md # vnext module boundaries and migration rules
│   ├── VNEXT_DATA_MODEL.md # vnext data model and state machines
│   ├── VNEXT_PHASE1_IMPLEMENTATION_PLAN.md # vnext phase-1 implementation plan
│   ├── VNEXT_SMART_COPILOT_UI_SPEC.md # vnext Smart Copilot UI specification
│   ├── VNEXT_AGENT_GATEWAY_DESIGN.md # vnext Agent Gateway and Provider Adapter design
│   ├── VNEXT_MIGRATION_PLAYBOOK.md # vnext migration playbook
│   ├── VNEXT_TEST_AND_ACCEPTANCE.md # vnext test and acceptance plan
│   └── VNEXT_IMPLEMENTATION_BACKLOG.md # vnext implementation backlog
├── personas/                     # AI role files (*.md)
├── asu-ide-extension/            # IDE companion extension (VSCode/Trae/Cursor)
├── tests/                        # Tests (unit / e2e / ablation)
├── scripts/                      # Daemon/launch scripts
├── smart_copilot.py              # GUI entry
├── smart_copilot_api.py          # API entry
└── pyproject.toml
```

---

## Documentation

| Document | Content |
|----------|---------|
| [USER_GUIDE.md](USER_GUIDE.md) | User manual (interactions, features, permissions, FAQ) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture design (Pipeline, Agent Loop, Skill system, Broker protocol) |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Development guide (module development, testing, adding Persona/Skill) |
| [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md) | Startup matrix for Agent / Broker / API Gateway / UI |
| [docs/UI_Redesign_Plan_v5.md](docs/UI_Redesign_Plan_v5.md) | v5.0 UI redesign plan (3-Tab architecture, Workspace 2.0, unified settings) |
| [docs/VNEXT_REBUILD_BLUEPRINT.md](docs/VNEXT_REBUILD_BLUEPRINT.md) | vnext rebuild blueprint focused on double-right-click Smart Copilot, API decoupling, and new-directory reconstruction |
| [docs/VNEXT_UNIFIED_AGENT_API.md](docs/VNEXT_UNIFIED_AGENT_API.md) | vnext unified Agent API contract (Task / Event / Result / Apply / SSE) |
| [docs/VNEXT_DOC_INDEX.md](docs/VNEXT_DOC_INDEX.md) | vnext document index with reading paths, document map, and review checkpoints |
| [docs/VNEXT_MODULE_BOUNDARIES.md](docs/VNEXT_MODULE_BOUNDARIES.md) | vnext directory layout, dependency boundaries, and migration rules |
| [docs/VNEXT_DATA_MODEL.md](docs/VNEXT_DATA_MODEL.md) | vnext data model and state machines for Task / Session / Context / Event / Apply |
| [docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md](docs/VNEXT_PHASE1_IMPLEMENTATION_PLAN.md) | vnext phase-1 implementation plan with sequence, deliverables, risks, and acceptance criteria |
| [docs/VNEXT_SMART_COPILOT_UI_SPEC.md](docs/VNEXT_SMART_COPILOT_UI_SPEC.md) | vnext Smart Copilot UI specification (floating panel, state machine, component split) |
| [docs/VNEXT_AGENT_GATEWAY_DESIGN.md](docs/VNEXT_AGENT_GATEWAY_DESIGN.md) | vnext Agent Gateway and Provider Adapter design (gateway roles, adapters, normalization strategies) |
| [docs/VNEXT_MIGRATION_PLAYBOOK.md](docs/VNEXT_MIGRATION_PLAYBOOK.md) | vnext migration playbook (old-to-new mapping, cutover order, deletion strategy) |
| [docs/VNEXT_TEST_AND_ACCEPTANCE.md](docs/VNEXT_TEST_AND_ACCEPTANCE.md) | vnext test and acceptance plan (contract tests, golden flows, cutover gates) |
| [docs/VNEXT_IMPLEMENTATION_BACKLOG.md](docs/VNEXT_IMPLEMENTATION_BACKLOG.md) | vnext implementation backlog (epics, stories, priorities, dependencies) |

---

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| P0 | Basic interaction, multi-engine AI, context awareness | ✅ |
| P1 | Privileged Broker, multimodal vision, silent text selection | ✅ |
| P2 | Persona workshop, PPT co-creation, Knowledge Graph, Skill architecture | ✅ |
| P3 | Agent Loop refactor, OpenClaw single-process migration, Pipeline unification | ✅ |
| P4 | Layered architecture refactor, code governance, full-chain observability | ✅ |
| P5 | v5.0 UI redesign: 3-Tab architecture, Workspace 2.0, unified settings, Skill refactoring | 🔶 In Progress (Studio Completed) |
| P6 | IDE Extension v2, Broker productization | 📋 Planned |
| P7 | Proactive context awareness, multi-agent collaboration | 📋 Planned |

---

## License

MIT © OpenCopilot Team
