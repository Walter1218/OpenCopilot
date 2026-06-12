import {
  Stack,
  Row,
  Grid,
  H1,
  H2,
  H3,
  Text,
  Card,
  CardHeader,
  CardBody,
  Button,
  Tag,
  Pill,
  Input,
  TextArea,
  Select,
  Progress,
  Callout,
  Divider,
  Spacer,
  useCanvasState,
} from "qoder/canvas";

// ── Shared: Annotation note ─────────────────────────────────────────────────
function Note({ n, title, desc, color = "#4da6ff" }: { n: number; title: string; desc: string; color?: string }) {
  return (
    <div style={{ border: `1px solid ${color}44`, borderLeft: `3px solid ${color}`, borderRadius: 6, padding: "10px 14px", background: `${color}0a` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <div style={{ width: 22, height: 22, borderRadius: "50%", background: color, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, flexShrink: 0 }}>{n}</div>
        <span style={{ fontWeight: 600, fontSize: 13, color: "#e0e0e0" }}>{title}</span>
      </div>
      <div style={{ fontSize: 12, color: "#999", lineHeight: 1.5, paddingLeft: 30 }}>{desc}</div>
    </div>
  );
}

// ── Shared: Traffic lights ──────────────────────────────────────────────────
function Dots() {
  return (
    <div style={{ display: "flex", gap: 7, alignItems: "center" }}>
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
      <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
    </div>
  );
}

// ── Shared: Window frame ────────────────────────────────────────────────────
function WinFrame({ title, badge, children }: { title: string; badge?: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "#1e1e1e", border: "1px solid #3c3c3c", borderRadius: 10, overflow: "hidden" }}>
      <div style={{ background: "#252526", padding: "10px 16px", display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid #3c3c3c" }}>
        <Dots />
        <span style={{ fontSize: 12, color: "#ccc", fontWeight: 600, flex: 1, textAlign: "center" }}>{title}</span>
        {badge && <div style={{ fontSize: 9, color: "#888", background: "#252526", border: "1px solid #3c3c3c", padding: "2px 8px", borderRadius: 10 }}>{badge}</div>}
      </div>
      {children}
    </div>
  );
}

// ── Shared: Tab bar ─────────────────────────────────────────────────────────
function TabBar({ tabs, active, onSelect }: { tabs: string[]; active: number; onSelect: (i: number) => void }) {
  return (
    <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #3c3c3c", background: "#1a1a1a" }}>
      {tabs.map((t, i) => (
        <div key={i} onClick={() => onSelect(i)} style={{
          padding: "8px 18px", cursor: "pointer", fontSize: 12, fontWeight: active === i ? 700 : 400,
          color: active === i ? "#4da6ff" : "#888",
          borderBottom: active === i ? "2px solid #4da6ff" : "2px solid transparent",
          background: active === i ? "#4da6ff0a" : "transparent",
        }}>{t}</div>
      ))}
    </div>
  );
}

// ── V5Plus helpers ──────────────────────────────────────────────────────────
const v5Strategies = [
  { icon: "\u25B2", name: "\u91D1\u5B57\u5854\u5F0F", sub: "\u7ED3\u8BBA\u5148\u884C", desc: "\u5148\u7ED9\u6838\u5FC3\u7ED3\u8BBA\uFF0C\u518D\u7528\u6570\u636E\u5C42\u5C42\u652F\u6491", struct: ["\u6838\u5FC3\u7ED3\u8BBA", "\u652F\u6491\u8BBA\u636E", "\u6570\u636E\u8BC1\u636E", "\u4E0B\u4E00\u6B65"], accent: "#4da6ff" },
  { icon: "\u25C6", name: "\u53D9\u4E8B\u5F0F", sub: "\u95EE\u9898\u9A71\u52A8", desc: "\u4ECE\u75DB\u70B9\u51FA\u53D1\uFF0C\u8BB2\u8FF0\u89E3\u51B3\u601D\u8DEF\u4E0E\u6536\u76CA", struct: ["\u73B0\u72B6\u75DB\u70B9", "\u89E3\u51B3\u601D\u8DEF", "\u6280\u672F\u5B9E\u73B0", "\u9884\u671F\u6536\u76CA"], accent: "#28a745" },
  { icon: "\u25C7", name: "\u5BF9\u6BD4\u5F0F", sub: "\u65B9\u6848\u8BBA\u8BC1", desc: "\u5448\u73B0\u591A\u65B9\u6848\u4F18\u52A3\uFF0C\u6570\u636E\u8BBA\u8BC1\u63A8\u8350", struct: ["\u80CC\u666F\u9700\u6C42", "\u65B9\u6848\u5BF9\u6BD4", "\u63A8\u8350\u8BE6\u89E3", "\u5B9E\u65BD\u98CE\u9669"], accent: "#ffc107" },
];
const v5Slides = [
  { title: "\u5C01\u9762", layout: "center" },
  { title: "\u6838\u5FC3\u7ED3\u8BBA", layout: "text" },
  { title: "\u4E09\u5927\u652F\u6491", layout: "3-col" },
  { title: "\u6570\u636E\u5BF9\u6BD4", layout: "chart", badge: "!" },
  { title: "\u6267\u884C\u8BA1\u5212", layout: "timeline" },
  { title: "Q&A", layout: "center" },
];

function StratCard({ icon, name, sub, desc, struct, selected, onSelect, accent }: {
  icon: string; name: string; sub: string; desc: string;
  struct: string[]; selected: boolean; onSelect: () => void; accent: string;
}) {
  return (
    <div onClick={onSelect} style={{
      flex: 1, cursor: "pointer", borderRadius: 8, padding: "12px 12px 10px",
      background: selected ? `${accent}18` : "#252526",
      border: selected ? `2px solid ${accent}` : "1px solid #3c3c3c",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: selected ? `${accent}40` : "#2d2d2d",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, color: selected ? accent : "#888",
        }}>{icon}</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: selected ? accent : "#e0e0e0" }}>{name}</div>
          <div style={{ fontSize: 11, color: "#888" }}>{sub}</div>
        </div>
        {selected && (
          <div style={{ marginLeft: "auto", width: 16, height: 16, borderRadius: "50%", background: accent, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#fff" }}>{"\u2713"}</div>
        )}
      </div>
      <div style={{ fontSize: 11, color: "#aaa", lineHeight: 1.5 }}>{desc}</div>
      <div style={{ background: "#1e1e1e", borderRadius: 5, padding: "6px 8px" }}>
        {struct.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: i < struct.length - 1 ? 3 : 0 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, background: selected ? `${accent}30` : "#2d2d2d", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, color: selected ? accent : "#888", fontWeight: 700 }}>{i + 1}</div>
            <span style={{ fontSize: 10, color: "#bbb" }}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Thumb({ idx, title, active }: { idx: number; title: string; active?: boolean }) {
  return (
    <div style={{ width: 64, flexShrink: 0, cursor: "pointer" }}>
      <div style={{
        width: 64, height: 36, borderRadius: 3,
        border: active ? "2px solid #4da6ff" : "1px solid #3c3c3c",
        background: active ? "#1a3a5c" : "#252526",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 3,
      }}>
        <div style={{ fontSize: 6, color: "#ccc", fontWeight: 600, textAlign: "center" }}>{title}</div>
      </div>
      <div style={{ textAlign: "center", fontSize: 9, color: active ? "#4da6ff" : "#888", marginTop: 2 }}>{idx + 1}</div>
    </div>
  );
}

function MiniDiff() {
  return (
    <div style={{ borderRadius: 5, border: "1px solid #3c3c3c", overflow: "hidden", fontSize: 10 }}>
      <div style={{ padding: "4px 8px", background: "#2a1a1a", borderBottom: "1px solid #3c3c3c", display: "flex", gap: 6 }}>
        <span style={{ color: "#ff6b6b", fontWeight: 700 }}>-</span>
        <span style={{ textDecoration: "line-through", color: "#cc8888" }}>2026 \u5E74\u5EA6\u53D1\u5C55\u603B\u7ED3</span>
      </div>
      <div style={{ padding: "4px 8px", background: "#1a2a1a", display: "flex", gap: 6 }}>
        <span style={{ color: "#6bff6b", fontWeight: 700 }}>+</span>
        <span style={{ color: "#88cc88" }}>2026 \u667A\u80FD\u4F53\u53D1\u5C55\u62A5\u544A\uFF1A\u591A\u6A21\u6001\u4E0E\u4EBA\u673A\u534F\u540C</span>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN CANVAS
// ════════════════════════════════════════════════════════════════════════════
export default function OpenCopilotUIInteraction() {
  const [tab, setTab] = useCanvasState<number>("main-tab", 0);
  const [scTab, setScTab] = useCanvasState<number>("sc-tab", 0);
  const [v5Stage, setV5Stage] = useCanvasState<number>("v5-stage", 0);
  const [selStrat, setSelStrat] = useCanvasState<number>("v5-strat", 0);
  const [selSlide, setSelSlide] = useCanvasState<number>("v5-slide", 0);

  const tabs = ["Smart Copilot", "Workspace", "Studio", "V5Plus", "Journey", "Connectors"];

  const connectors = [
    { from: "SC / Work", to: "SC / Chat", trigger: "Follow-up", value: "Auto-carry context + result summary" },
    { from: "SC / Studio", to: "Studio", trigger: "Open Studio", value: "Text into PPT co-creation" },
    { from: "SC / Studio", to: "V5Plus", trigger: "[V5Plus] button", value: "Route: no text->S0, has text->S1" },
    { from: "SC", to: "Workspace", trigger: "Task upgrade", value: "Local action -> persistent task" },
    { from: "WS / Files", to: "Studio", trigger: "Send to Studio", value: "Files as creation context" },
    { from: "V5P / S2", to: "SC / Chat", trigger: "Post-export (TODO)", value: "Export result back to conversation" },
    { from: "V5Plus", to: "Studio", trigger: "Window mutex", value: "Open one, close the other" },
  ];

  return (
    <div style={{ background: "#111", minHeight: "100vh", padding: 20, boxSizing: "border-box" }}>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <H1>OpenCopilot UI Interaction</H1>
        <Text tone="secondary" size="small">v2.1 | Work Tab redesigned: compact toolbar + hero result area | 2026-06-11</Text>
        <Spacer />

        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 20 }}>
          {tabs.map((t, i) => (
            <button key={i} onClick={() => setTab(i)} style={{
              padding: "6px 14px", borderRadius: 20, cursor: "pointer",
              fontSize: 11, fontWeight: tab === i ? 700 : 500,
              border: tab === i ? "1px solid #4da6ff" : "1px solid #3c3c3c",
              background: tab === i ? "#4da6ff22" : "transparent",
              color: tab === i ? "#4da6ff" : "#888",
            }}>{t}</button>
          ))}
        </div>
        <Divider />
        <Spacer />

        {/* ═══════════════ TAB 0: SMART COPILOT ═══════════════ */}
        {tab === 0 && (
          <Stack gap={16}>
            <H2>Smart Copilot — Work Tab (Redesigned)</H2>
            <Text tone="secondary" size="small">双击右键唤起，680 x 520。精简 3 层：Header → Toolbar → Result (Hero)。</Text>

            <WinFrame title="Smart Copilot" badge="680 x 520">
              <TabBar tabs={["Work", "Chat", "Studio"]} active={scTab} onSelect={setScTab} />

              {/* ── Work Tab (Redesigned) ── */}
              {scTab === 0 && (
                <div style={{ display: "flex", flexDirection: "column", height: 440 }}>
                  {/* Context header bar */}
                  <div style={{ padding: "8px 20px", borderBottom: "1px solid #333", background: "#1a1a1a", display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#4da6ff", boxShadow: "0 0 6px #4da6ff88" }} />
                      <span style={{ fontSize: 11, fontWeight: 600, color: "#e0e0e0" }}>Selection</span>
                    </div>
                    <div style={{ width: 1, height: 14, background: "#3c3c3c" }} />
                    <span style={{ fontSize: 10, color: "#888" }}>236 chars</span>
                    <div style={{ width: 1, height: 14, background: "#3c3c3c" }} />
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <div style={{ width: 14, height: 14, borderRadius: 3, background: "#4da6ff22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, color: "#4da6ff", fontWeight: 700 }}>VS</div>
                      <span style={{ fontSize: 10, color: "#666" }}>VS Code</span>
                    </div>
                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 9, color: "#555", border: "1px dashed #444", padding: "2px 8px", borderRadius: 4 }}>drop here</span>
                      <div style={{ width: 18, height: 18, borderRadius: 4, background: "#252526", border: "1px solid #3c3c3c", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#666", cursor: "pointer" }}>↻</div>
                      <div style={{ width: 18, height: 18, borderRadius: 4, background: "#252526", border: "1px solid #3c3c3c", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#666", cursor: "pointer" }}>✕</div>
                    </div>
                  </div>

                  {/* Toolbar row: sources + actions (single line ~40px) */}
                  <div style={{ padding: "8px 20px", display: "flex", alignItems: "center", gap: 6, borderBottom: "1px solid #2d2d2d", background: "#1e1e1e" }}>
                    {[
                      { l: "S", active: true },
                      { l: "D" },
                      { l: "B" },
                      { l: "C" },
                      { l: "F" },
                    ].map((s, i) => (
                      <div key={i} style={{
                        width: 24, height: 24, borderRadius: 4, fontSize: 10, cursor: "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: s.active ? "#4da6ff22" : "#252526",
                        border: s.active ? "1px solid #4da6ff55" : "1px solid #3c3c3c",
                        color: s.active ? "#4da6ff" : "#666",
                        fontWeight: s.active ? 700 : 400,
                      }}>{s.l}</div>
                    ))}
                    <div style={{ width: 1, height: 18, background: "#3c3c3c", margin: "0 4px" }} />
                    {[
                      { label: "Explain", icon: "📖", accent: "#4da6ff", primary: true },
                      { label: "Fix", icon: "🔧", accent: "#28a745", primary: true },
                      { label: "Polish", icon: "✨", accent: "#ffc107", primary: true },
                      { label: "Translate", icon: "🌐", accent: "#888", primary: false },
                      { label: "Review", icon: "🔍", accent: "#888", primary: false },
                    ].map((a, i) => (
                      <div key={i} style={{
                        display: "flex", alignItems: "center", gap: 5,
                        padding: "5px 10px", borderRadius: 5, cursor: "pointer",
                        background: a.primary ? `${a.accent}12` : "#252526",
                        border: a.primary ? `1px solid ${a.accent}33` : "1px solid #3c3c3c",
                        fontSize: 11, color: a.primary ? a.accent : "#999",
                        fontWeight: a.primary ? 600 : 400,
                      }}>
                        <span style={{ fontSize: 12 }}>{a.icon}</span>
                        {a.label}
                      </div>
                    ))}
                    <div style={{ marginLeft: "auto", fontSize: 9, color: "#555", background: "#252526", padding: "2px 8px", borderRadius: 3, border: "1px solid #333" }}>→ Chat</div>
                  </div>

                  {/* Result area (HERO — flex:1 fills remaining space) */}
                  <div style={{ flex: 1, margin: "10px 20px 0", borderRadius: 8, border: "1px solid #3c3c3c", overflow: "hidden", display: "flex", flexDirection: "column" }}>
                    <div style={{ padding: "7px 14px", background: "#252526", borderBottom: "1px solid #3c3c3c", display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 11 }}>📖</span>
                      <span style={{ fontSize: 11, fontWeight: 600, color: "#e0e0e0" }}>Explain Result</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: "auto" }}>
                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#28a745", boxShadow: "0 0 4px #28a745" }} />
                        <span style={{ fontSize: 9, color: "#28a745" }}>Streaming...</span>
                      </div>
                    </div>
                    <div style={{ flex: 1, padding: "14px 16px", background: "#1a1a1a", overflow: "auto" }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#e0e0e0", marginBottom: 8 }}>Function: process_selection</div>
                      <div style={{ fontSize: 11, color: "#bbb", lineHeight: 1.7, marginBottom: 10 }}>
                        This async function takes a text selection and its source identifier, then analyzes the context to produce a structured result dictionary.
                      </div>
                      <div style={{ background: "#252526", borderRadius: 5, padding: "8px 12px", marginBottom: 10, border: "1px solid #333" }}>
                        <div style={{ fontSize: 9, color: "#888", marginBottom: 4 }}>Key Operations:</div>
                        <div style={{ fontSize: 10, color: "#aaa", lineHeight: 1.8, paddingLeft: 8 }}>• 1. Parse selection boundaries and validate input</div>
                        <div style={{ fontSize: 10, color: "#aaa", lineHeight: 1.8, paddingLeft: 8 }}>• 2. Call analyze_context() for structural analysis</div>
                        <div style={{ fontSize: 10, color: "#aaa", lineHeight: 1.8, paddingLeft: 8 }}>• 3. Build and return structured dict with findings</div>
                      </div>
                      <div style={{ fontSize: 11, color: "#4da6ff", lineHeight: 1.7 }}>
                        The function follows a pipeline pattern: input validation → context extraction → result formatting...
                      </div>
                    </div>
                    <div style={{ padding: "6px 14px", background: "#252526", borderTop: "1px solid #333", display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 9, color: "#666" }}>Confidence:</span>
                      <div style={{ width: 60, height: 3, borderRadius: 2, background: "#333", overflow: "hidden" }}>
                        <div style={{ width: "87%", height: "100%", background: "#28a745", borderRadius: 2 }} />
                      </div>
                      <span style={{ fontSize: 9, color: "#28a745", fontWeight: 600 }}>87%</span>
                      <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 3, padding: "3px 8px", borderRadius: 4, background: "#1e1e1e", border: "1px solid #3c3c3c", fontSize: 9, color: "#aaa", cursor: "pointer" }}>📋 Copy</div>
                        <div style={{ display: "flex", alignItems: "center", gap: 3, padding: "3px 8px", borderRadius: 4, background: "#1e1e1e", border: "1px solid #3c3c3c", fontSize: 9, color: "#aaa", cursor: "pointer" }}>📤 Export</div>
                        <div style={{ display: "flex", alignItems: "center", gap: 3, padding: "3px 10px", borderRadius: 4, background: "#28a745", fontSize: 9, color: "#fff", fontWeight: 600, cursor: "pointer" }}>✓ Apply</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Chat Tab ── */}
              {scTab === 1 && (
                <div style={{ padding: "16px 20px", minHeight: 260 }}>
                  <div style={{ background: "#252526", border: "1px solid #3c3c3c", borderRadius: 6, padding: 10, marginBottom: 10, display: "flex", gap: 8 }}>
                    <span style={{ fontSize: 9, color: "#4da6ff", background: "#4da6ff18", padding: "2px 6px", borderRadius: 8, border: "1px solid #4da6ff44", flexShrink: 0 }}>Context</span>
                    <span style={{ fontSize: 10, color: "#888", flex: 1 }}>Auto-injected from Work tab</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
                    <div style={{ maxWidth: 220, padding: "6px 10px", borderRadius: 8, fontSize: 11, lineHeight: 1.5, background: "#4da6ff", color: "#fff" }}>Can you explain this function?</div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 16 }}>
                    <div style={{ maxWidth: 260, padding: "6px 10px", borderRadius: 8, fontSize: 11, lineHeight: 1.5, background: "#2d2d2d", color: "#d4d4d4", border: "1px solid #3c3c3c" }}>Sure! This function takes the selected code and...</div>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Input placeholder="Follow up..." />
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#4da6ff", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 11, cursor: "pointer", flexShrink: 0 }}>▶</div>
                  </div>
                </div>
              )}

              {/* ── Studio Tab ── */}
              {scTab === 2 && (
                <div style={{ padding: "20px 24px", minHeight: 260, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e0e0" }}>PPT Co-Creation</div>
                  <div style={{ fontSize: 11, color: "#888", textAlign: "center", lineHeight: 1.6 }}>Create professional presentations from your documents</div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button style={{ padding: "8px 20px", borderRadius: 6, border: "1px solid #3c3c3c", background: "transparent", color: "#ccc", fontSize: 11, cursor: "pointer" }}>Open Studio</button>
                    <button style={{ padding: "8px 20px", borderRadius: 6, border: "none", background: "#6f42c1", color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>V5Plus CoCreation</button>
                  </div>
                  <TextArea rows={3} placeholder="Quick paste text here to start..." />
                </div>
              )}
            </WinFrame>

            <Grid columns={3} gap={12}>
              <Note n={1} title="Header + Drop Zone" desc="顶部状态栏精简：发光圆点 + 来源 + 字数 + 宿主 app。右侧 drop here 提示拖拽获取上下文，无需单独 Selection Preview。" color="#4da6ff" />
              <Note n={2} title="Toolbar Row" desc="单行工具栏：5个数据源 icon 按钮（字母缩写）+ 分割线 + 5个操作按钮。Explain/Fix/Polish 三色高亮，Translate/Review 中性色。去掉卡片式大按钮。" color="#28a745" />
              <Note n={3} title="Result = Hero" desc="Result Area 占满剩余空间（flex:1）。底部合并 Confidence Bar + Copy/Export/Apply 为单行，不再单独占用 Action Bar。" color="#ffc107" />
            </Grid>
          </Stack>
        )}

        {/* ═══════════════ TAB 1: WORKSPACE ═══════════════ */}
        {tab === 1 && (
          <Stack gap={16}>
            <H2>Agent Workspace — 复杂任务工作台</H2>
            <Text tone="secondary" size="small">三击右键唤起，1000 x 700。任务定义 + 文件组织 + 记忆注入 + 多轮协作。</Text>

            <WinFrame title="Agent Workspace" badge="1000 x 700">
              <div style={{ display: "flex", height: 380, overflow: "hidden" }}>
                <div style={{ width: 160, borderRight: "1px solid #333", background: "#1a1a1a", padding: "12px 0" }}>
                  {["Task", "Chat", "Files", "Memory", "Settings"].map((item, i) => (
                    <div key={i} style={{
                      padding: "8px 16px", fontSize: 12, cursor: "pointer",
                      color: i === 0 ? "#4da6ff" : "#888",
                      background: i === 0 ? "#4da6ff0a" : "transparent",
                      borderLeft: i === 0 ? "2px solid #4da6ff" : "2px solid transparent",
                    }}>{item}</div>
                  ))}
                </div>
                <div style={{ flex: 1, padding: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#e0e0e0", marginBottom: 6 }}>Task: Quarterly Report Analysis</div>
                  <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                    <span style={{ fontSize: 9, color: "#28a745", background: "#28a74518", padding: "2px 8px", borderRadius: 10, border: "1px solid #28a74544" }}>Active</span>
                    <span style={{ fontSize: 9, color: "#888", background: "#252526", padding: "2px 8px", borderRadius: 10, border: "1px solid #3c3c3c" }}>Template: Report</span>
                  </div>
                  <div style={{ background: "#252526", border: "1px solid #3c3c3c", borderRadius: 6, padding: 12, marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>Task Description</div>
                    <div style={{ fontSize: 11, color: "#ccc", lineHeight: 1.6 }}>Analyze Q2 data across all departments and produce a summary presentation.</div>
                  </div>
                  <div style={{ background: "#252526", border: "1px solid #3c3c3c", borderRadius: 6, overflow: "hidden" }}>
                    <div style={{ padding: "8px 12px", borderBottom: "1px solid #333", fontSize: 11, fontWeight: 600, color: "#ccc" }}>Files (3)</div>
                    {[
                      { f: "q2_sales_data.xlsx", s: "2.4 MB", c: "#28a745" },
                      { f: "department_notes.md", s: "12 KB", c: "#4da6ff" },
                      { f: "prev_report.pptx", s: "890 KB", c: "#ffc107" },
                    ].map((file, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", padding: "6px 12px", gap: 8, borderBottom: i < 2 ? "1px solid #2d2d2d" : "none" }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: file.c, flexShrink: 0 }} />
                        <span style={{ flex: 1, fontSize: 11, color: "#ccc", fontFamily: "monospace" }}>{file.f}</span>
                        <span style={{ fontSize: 10, color: "#666" }}>{file.s}</span>
                        <span style={{ fontSize: 9, color: "#4da6ff", cursor: "pointer" }}>Send</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </WinFrame>

            <Grid columns={3} gap={12}>
              <Note n={1} title="稳定导航" desc="左侧 Sidebar 始终可见：Task/Chat/Files/Memory/Settings。" color="#4da6ff" />
              <Note n={2} title="任务锚点" desc="Task 面板是 Chat/Files/Memory 的共同锚点。" color="#28a745" />
              <Note n={3} title="文件即上下文" desc="Files 面板支持筛选、预览、一键发送到 Chat 或 Studio。" color="#ffc107" />
            </Grid>
          </Stack>
        )}

        {/* ═══════════════ TAB 2: STUDIO ═══════════════ */}
        {tab === 2 && (
          <Stack gap={16}>
            <H2>Studio (Legacy) — 4-Panel PPT 工作台</H2>
            <Text tone="secondary" size="small">专业 PPT 工作台。Source / Outline / Preview / AI Zone 四面板布局。</Text>

            <WinFrame title="PPT CoCreation" badge="Slides: 8">
              <div style={{ display: "flex", gap: 12, padding: "6px 16px", borderBottom: "1px solid #333", background: "#1a1a1a" }}>
                <span style={{ fontSize: 10, color: "#888" }}>Slides: <b style={{ color: "#4da6ff" }}>8</b></span>
                <span style={{ fontSize: 10, color: "#888" }}>Bullets: <b style={{ color: "#28a745" }}>24</b></span>
                <span style={{ fontSize: 10, color: "#888" }}>Source: <b style={{ color: "#ffc107" }}>67%</b></span>
              </div>
              <div style={{ display: "flex", height: 300, overflow: "hidden" }}>
                <div style={{ width: "25%", borderRight: "1px solid #333", padding: 10 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: "#ccc", marginBottom: 8 }}>📄 Source</div>
                  <div style={{ padding: "5px 8px", marginBottom: 6, borderRadius: 4, fontSize: 9, lineHeight: 1.6, color: "#ccc", background: "#4da6ff0a", border: "1px solid #4da6ff22" }}>2026年，智能体技术在多个领域... <span style={{ fontSize: 7, color: "#4da6ff" }}>→S2</span></div>
                  <div style={{ padding: "5px 8px", marginBottom: 6, borderRadius: 4, fontSize: 9, lineHeight: 1.6, color: "#666" }}>以下是我们对本年度发展的...</div>
                  <div style={{ padding: "5px 8px", borderRadius: 4, fontSize: 9, lineHeight: 1.6, color: "#ccc", background: "#4da6ff0a", border: "1px solid #4da6ff22" }}>多模态感知能力的提升是最... <span style={{ fontSize: 7, color: "#4da6ff" }}>→S3</span></div>
                </div>
                <div style={{ width: "30%", borderRight: "1px solid #333", padding: 10 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: "#ccc", marginBottom: 8 }}>Outline</div>
                  {["封面 - center", "核心结论 - text", "三大支撑 - 3-col", "数据对比 - chart", "执行计划 - timeline"].map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 8px", marginBottom: 4, borderRadius: 4, background: i === 0 ? "#4da6ff15" : "transparent" }}>
                      <div style={{ width: 28, height: 16, borderRadius: 2, background: "#252526", border: "1px solid #3c3c3c", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 6, color: "#888" }}>{i + 1}</div>
                      <span style={{ fontSize: 10, color: "#bbb" }}>{s}</span>
                    </div>
                  ))}
                </div>
                <div style={{ flex: 1, padding: 16, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <div style={{ width: "90%", aspectRatio: "16/9", background: "#fafafc", borderRadius: 5, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 16 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#1a1a2e", padding: "2px 6px", border: "2px dashed #4da6ff", borderRadius: 3 }}>封面</div>
                    <div style={{ fontSize: 7, color: "#4da6ff", marginTop: 4 }}>Click-to-Edit</div>
                  </div>
                </div>
              </div>
              <div style={{ borderTop: "1px solid #333", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8, background: "#1a1a1a" }}>
                <span style={{ fontSize: 10, color: "#4da6ff", fontWeight: 600 }}>🤖 AI:</span>
                <div style={{ flex: 1, padding: "5px 10px", borderRadius: 5, background: "#252526", border: "1px solid #3c3c3c", fontSize: 10, color: "#666" }}>把第2页标题改得更简短...</div>
                <Button variant="primary">Send</Button>
              </div>
            </WinFrame>

            <Grid columns={4} gap={10}>
              <Note n={1} title="Source" desc="原文全文，已用段落高亮+点击跳页。" color="#4da6ff" />
              <Note n={2} title="Outline" desc="缩略图导航+标题+版式标注。" color="#28a745" />
              <Note n={3} title="Preview" desc="Click-to-Edit + AI Diff Overlay。" color="#ffc107" />
              <Note n={4} title="AI Zone" desc="自然语言指令，AI diff 叠加预览。" color="#6f42c1" />
            </Grid>
          </Stack>
        )}

        {/* ═══════════════ TAB 3: V5Plus ═══════════════ */}
        {tab === 3 && (
          <Stack gap={16}>
            <H2>V5Plus CoCreation — 3-Stage E2E</H2>
            <Text tone="secondary" size="small">Studio 演进版。从原文输入到最终 PPT：连续、无跳转的 3 阶段交互。</Text>

            {/* Stage nav */}
            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              {[{ label: "1 输入原文", short: "输入" }, { label: "2 策略发现", short: "策略" }, { label: "3 编辑打磨", short: "编辑" }].map((s, i) => (
                <button key={i} onClick={() => setV5Stage(i)} style={{
                  padding: "6px 16px", borderRadius: 20, cursor: "pointer",
                  fontSize: 12, fontWeight: v5Stage === i ? 700 : 500,
                  border: v5Stage === i ? "1px solid #4da6ff" : "1px solid #3c3c3c",
                  background: v5Stage === i ? "#4da6ff22" : "transparent",
                  color: v5Stage === i ? "#4da6ff" : "#888",
                }}>{s.label}</button>
              ))}
            </div>

            {/* ── Stage 1: Text Input ── */}
            {v5Stage === 0 && (
              <WinFrame title="V5Plus CoCreation" badge="Stage 1">
                <div style={{ padding: "8px 28px", background: "#1a2a1a", borderBottom: "1px solid #333", fontSize: 10, color: "#4caf50", display: "flex", alignItems: "center", gap: 6 }}>
                  <span>{"\u2139\uFE0F"}</span>
                  <span>有文本时（Work Tab 选中 / 剪贴板 / 拖放文件）自动跳过此页，直接进入 Stage 2 策略发现</span>
                </div>
                <div style={{ padding: "24px 28px" }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#e0e0e0", marginBottom: 16 }}>粘贴或输入你的原文</div>
                  <TextArea rows={6} placeholder="在此粘贴文档内容...支持技术方案、工作报告、产品介绍等任意文本。" />
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
                    <div style={{ fontSize: 11, color: "#666" }}>已输入 2,847 字 / 检测到 6 个段落</div>
                    <button onClick={() => setV5Stage(1)} style={{ padding: "8px 24px", borderRadius: 6, border: "none", background: "#4da6ff", color: "#fff", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>分析文档结构 {"\u2192"}</button>
                  </div>
                </div>
              </WinFrame>
            )}

            {/* ── Stage 2: Strategy Discovery ── */}
            {v5Stage === 1 && (
              <WinFrame title="V5Plus - 策略发现" badge="Stage 2">
                <div style={{ padding: "20px 24px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#e0e0e0" }}>文档分析</span>
                    <div style={{ background: "#6f42c122", border: "1px solid #6f42c166", color: "#6f42c1", fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 10 }}>技术方案</div>
                    <span style={{ fontSize: 11, color: "#666" }}>2,847 字</span>
                  </div>
                  <div style={{ display: "flex", gap: 2, marginBottom: 12 }}>
                    {[{ l: "背景", c: "#dc3545", w: 2 }, { l: "架构", c: "#4da6ff", w: 3 }, { l: "数据", c: "#28a745", w: 2 }, { l: "对比", c: "#ffc107", w: 2 }, { l: "流程", c: "#17a2b8", w: 3 }, { l: "总结", c: "#6f42c1", w: 1 }].map((p, i) => (
                      <div key={i} style={{ flex: p.w, height: 24, background: p.c, borderRadius: 3, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#fff", fontWeight: 500, opacity: 0.85 }}>{p.l}</div>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#e0e0e0", marginBottom: 10 }}>选择叙事策略<span style={{ fontSize: 11, color: "#888", fontWeight: 400, marginLeft: 8 }}>Agent 推荐，可自由调整</span></div>
                  <div style={{ display: "flex", gap: 10 }}>
                    {v5Strategies.map((s, i) => (
                      <StratCard key={i} icon={s.icon} name={s.name} sub={s.sub} desc={s.desc} struct={s.struct} selected={selStrat === i} onSelect={() => setSelStrat(i)} accent={s.accent} />
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>目标受众（可选）</div>
                      <Input placeholder="如：技术总监、产品经理..." />
                    </div>
                    <div style={{ flex: "0 0 130px" }}>
                      <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>演讲时长</div>
                      <Select value="10min" options={[{ value: "5min", label: "5 分钟" }, { value: "10min", label: "10 分钟" }, { value: "15min", label: "15 分钟" }, { value: "30min", label: "30 分钟" }]} />
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
                    <button style={{ padding: "7px 18px", borderRadius: 6, border: "1px solid #3c3c3c", background: "transparent", color: "#888", fontSize: 12, cursor: "pointer" }}>跳过，直接生成</button>
                    <button onClick={() => setV5Stage(2)} style={{ padding: "7px 22px", borderRadius: 6, border: "none", background: "#4da6ff", color: "#fff", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>开始生成 {"\u2192"}</button>
                  </div>
                </div>
              </WinFrame>
            )}

            {/* ── Stage 3: Edit + Polish ── */}
            {v5Stage === 2 && (
              <WinFrame title="V5Plus - 编辑打磨" badge="Stage 3">
                <div style={{ display: "flex", height: 440, overflow: "hidden" }}>
                  {/* CENTER: PPT area (60%) */}
                  <div style={{ width: "60%", display: "flex", flexDirection: "column", borderRight: "1px solid #333" }}>
                    <div style={{ padding: "7px 10px", borderBottom: "1px solid #333", display: "flex", gap: 5, overflowX: "auto", background: "#1a1a1a" }}>
                      {v5Slides.map((s, i) => (
                        <Thumb key={i} idx={i} title={s.title} active={selSlide === i} />
                      ))}
                    </div>
                    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, position: "relative" }}>
                      <div style={{ width: "92%", aspectRatio: "16/9", background: "#fafafc", borderRadius: 5, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 16, position: "relative" }}>
                        {selSlide === 0 ? (
                          <>
                            <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e", padding: "4px 8px", border: "2px dashed #4da6ff", borderRadius: 3, cursor: "text", marginBottom: 8 }}>{v5Slides[selSlide].title}</div>
                            <div style={{ fontSize: 8, color: "#4da6ff" }}>双击编辑</div>
                          </>
                        ) : (
                          <>
                            <div style={{ fontSize: 13, fontWeight: 700, color: "#1a1a2e", marginBottom: 10, padding: "2px 6px", border: "2px dashed #4da6ff", borderRadius: 3, cursor: "text" }}>{v5Slides[selSlide].title}</div>
                            <div style={{ display: "flex", gap: 8, width: "80%" }}>
                              {[1, 2, 3].map((col) => (
                                <div key={col} style={{ flex: 1, background: "#e8e8ee", borderRadius: 3, padding: "8px 6px", fontSize: 7, color: "#555", lineHeight: 1.6 }}>
                                  <div style={{ fontWeight: 600, marginBottom: 3, color: "#333" }}>{"\u2022"} 要点 {col}</div>
                                  直接点击即可编辑
                                </div>
                              ))}
                            </div>
                          </>
                        )}
                        {selSlide === 0 && (
                          <div style={{ position: "absolute", top: 6, right: 6, width: 200, background: "#1e1e1eee", border: "1px solid #4da6ff44", borderRadius: 6, padding: 10, fontSize: 10 }}>
                            <div style={{ color: "#4da6ff", fontWeight: 600, marginBottom: 6, fontSize: 9 }}>{"\uD83E\uDD16"} AI 建议修改标题</div>
                            <MiniDiff />
                            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                              <div style={{ padding: "3px 10px", borderRadius: 4, background: "#28a745", color: "#fff", fontSize: 9, cursor: "pointer", fontWeight: 600 }}>{"\u2713"} 接受</div>
                              <div style={{ padding: "3px 10px", borderRadius: 4, background: "#dc3545", color: "#fff", fontSize: 9, cursor: "pointer", fontWeight: 600 }}>{"\u2717"} 拒绝</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    <div style={{ borderTop: "1px solid #333", padding: "6px 12px", background: "#1a1a1a", display: "flex", gap: 4 }}>
                      {["center", "text", "3-col", "chart", "timeline"].map((l) => (
                        <Tag key={l} active={v5Slides[selSlide].layout === l} tone={v5Slides[selSlide].layout === l ? "primary" : "neutral"} size="sm">{l}</Tag>
                      ))}
                    </div>
                  </div>
                  {/* RIGHT: Source (40%) */}
                  <div style={{ width: "40%", display: "flex", flexDirection: "column" }}>
                    <div style={{ padding: "6px 10px", background: "#252526", borderBottom: "1px solid #333", fontSize: 11, fontWeight: 600, color: "#ccc", display: "flex", alignItems: "center", gap: 6 }}>
                      <span>{"\uD83D\uDCC4"} 原文</span>
                      <div style={{ marginLeft: "auto", width: 50 }}><Progress value={72} format="percent" height={3} tone="info" /></div>
                    </div>
                    <div style={{ padding: 10, flex: 1, overflow: "auto" }}>
                      {[
                        { text: "2026年，智能体技术在多个领域取得了突破性进展...", slide: "S2", c: "#4da6ff", active: selSlide === 1 },
                        { text: "以下是我们对本年度发展的全面回顾...", slide: "+", c: "#666", active: false },
                        { text: "多模态感知能力的提升是最显著的突破之一...准确率提升了 40%...", slide: "S3", c: "#28a745", active: selSlide === 2 },
                        { text: "端侧本地化部署降低了延迟...推理延迟从 800ms 降至 120ms...", slide: "S4", c: "#ffc107", active: false },
                      ].map((p, i) => (
                        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 8, padding: "5px 8px", borderRadius: 4, background: p.active ? `${p.c}11` : "transparent", border: p.active ? `1px solid ${p.c}33` : "1px solid transparent" }}>
                          <span style={{ background: `${p.c}33`, padding: "2px 4px", borderRadius: 2, fontSize: 11, color: "#ccc", flex: 1, lineHeight: 1.8 }}>{p.text}</span>
                          <div style={{ fontSize: 8, fontWeight: 700, color: p.c, background: `${p.c}22`, border: `1px solid ${p.c}44`, padding: "1px 5px", borderRadius: 8, whiteSpace: "nowrap", cursor: "pointer", flexShrink: 0 }}>{p.slide}</div>
                        </div>
                      ))}
                    </div>
                    <div style={{ borderTop: "1px solid #333", padding: "8px 10px", background: "#1a1a1a" }}>
                      <div style={{ display: "flex", gap: 6 }}>
                        <div style={{ flex: 1, padding: "7px 10px", borderRadius: 6, background: "#252526", border: "1px solid #3c3c3c", fontSize: 11, color: "#888" }}>输入指令：改标题、调版式、移内容...</div>
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#4da6ff", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 11, cursor: "pointer", flexShrink: 0 }}>{"\u25B6"}</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "8px 14px", borderTop: "1px solid #333", background: "#1a1a1a" }}>
                  <button style={{ padding: "6px 18px", borderRadius: 5, border: "none", background: "#28a745", color: "#fff", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>{"\uD83D\uDCBE"} 导出 PPT</button>
                </div>
              </WinFrame>
            )}

            <Grid columns={3} gap={12}>
              <Note n={1} title="Stage 1 零配置" desc="无需选模板或配置参数，直接粘贴即可开始。有文本时自动跳过。" color="#4da6ff" />
              <Note n={2} title="Stage 2 策略注入" desc="修辞分析（<500ms）+ 策略推荐。选定策略注入 Pipeline prompt。" color="#28a745" />
              <Note n={3} title="Stage 3 IDE式编辑" desc="中间 PPT + 右侧原文。Click-to-Edit + AI Diff Overlay + 映射标签双向联动。" color="#ffc107" />
            </Grid>
          </Stack>
        )}

        {/* ═══════════════ TAB 4: JOURNEY ═══════════════ */}
        {tab === 4 && (
          <Stack gap={16}>
            <H2>Cross-Window Relay</H2>
            <Text tone="secondary">四个窗口之间的自然接力。</Text>
            <div style={{ background: "#1e1e1e", border: "1px solid #3c3c3c", borderRadius: 10, padding: "20px 24px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 12, color: "#888" }}>Any app</span>
                <span style={{ color: "#555" }}>→</span>
                <span style={{ fontSize: 11, color: "#4da6ff", background: "#4da6ff18", padding: "3px 10px", borderRadius: 10, border: "1px solid #4da6ff44" }}>Double Right-Click</span>
                <span style={{ color: "#555" }}>→</span>
                <span style={{ fontSize: 12, color: "#e0e0e0", fontWeight: 600 }}>Smart Copilot</span>
              </div>
              <div style={{ display: "flex", gap: 12, paddingLeft: 40 }}>
                {[
                  { label: "Work", desc: "Quick actions", c: "#4da6ff" },
                  { label: "Chat", desc: "Follow-up", c: "#28a745" },
                  { label: "Studio", desc: "PPT editor", c: "#ffc107" },
                ].map((w, i) => (
                  <div key={i} style={{ flex: 1, background: "#252526", border: `1px solid ${w.c}44`, borderRadius: 8, padding: "12px 14px", borderLeft: `3px solid ${w.c}` }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: w.c, marginBottom: 4 }}>{w.label}</div>
                    <div style={{ fontSize: 11, color: "#999" }}>{w.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </Stack>
        )}

        {/* ═══════════════ TAB 5: CONNECTORS ═══════════════ */}
        {tab === 5 && (
          <Stack gap={16}>
            <H2>Connectors — Inter-Window Data Flow</H2>
            <Text tone="secondary">跨窗口数据流向和触发关系。</Text>
            <div style={{ background: "#1e1e1e", border: "1px solid #3c3c3c", borderRadius: 8, overflow: "hidden" }}>
              {connectors.map((c, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", padding: "8px 14px", gap: 10, borderBottom: i < connectors.length - 1 ? "1px solid #2d2d2d" : "none", background: i % 2 === 0 ? "transparent" : "#1a1a1a" }}>
                  <div style={{ flex: "0 0 100px", fontSize: 11, color: "#4da6ff", fontWeight: 600 }}>{c.from}</div>
                  <span style={{ color: "#555", fontSize: 12 }}>→</span>
                  <div style={{ flex: "0 0 100px", fontSize: 11, color: "#28a745", fontWeight: 600 }}>{c.to}</div>
                  <div style={{ flex: "0 0 120px", fontSize: 10, color: "#ffc107", background: "#ffc10718", padding: "2px 6px", borderRadius: 4 }}>{c.trigger}</div>
                  <div style={{ flex: 1, fontSize: 10, color: "#888" }}>{c.value}</div>
                </div>
              ))}
            </div>
          </Stack>
        )}

        <div style={{ height: 40 }} />
      </div>
    </div>
  );
}
