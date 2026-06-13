import {
  Stack,
  Row,
  Grid,
  H1,
  H2,
  H3,
  Text,
  Button,
  Tag,
  Pill,
  Card,
  CardHeader,
  CardBody,
  Stat,
  Divider,
  Spacer,
  Callout,
  Select,
  Switch,
  Table,
  useCanvasState,
  useHostTheme,
} from "qoder/canvas";

export default function InteractionRedesign() {
  const { tokens } = useHostTheme();
  const [tab, setTab] = useCanvasState("main-tab", 0);
  const [wsPanel, setWsPanel] = useCanvasState("ws-panel", 0);
  const [v5Stage, setV5Stage] = useCanvasState("v5-stage", 0);
  const [selSlide, setSelSlide] = useCanvasState("v5-slide", 0);
  const [intent, setIntent] = useCanvasState("intent", 0);
  const [settingsSection, setSettingsSection] = useCanvasState("settings-section", 1);
  const [theme, setTheme] = useCanvasState("theme", 0);
  const [showStrat, setShowStrat] = useCanvasState("show-strat", false);
  const [aiDiffAccepted, setAiDiffAccepted] = useCanvasState("ai-diff-accepted", false);
  const [toggles, setToggles] = useCanvasState("toggles", {
    sourceChips: false, wordCount: false, persona: false, closeBtn: false,
    explain: false, summarize: false, polish: false, revise: false,
  });

  const tabLabels = ["Smart Copilot", "Workspace", "V5Plus CoCreate", "Settings", "Flows"];
  const stageLabels = ["1 输入原文", "2 生成", "3 编辑导出"];

  const toggleItem = (key: string) => {
    setToggles((prev: any) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Stack gap={20} style={{ maxWidth: 920, margin: "0 auto", padding: 20 }}>
      <H1>OpenCopilot v5 Interaction Redesign</H1>
      <Text tone="secondary" size="small">v5.0 | 全交互跳转补全 | 2026-06-12</Text>
      <Spacer />

      <Grid columns={5} gap={10}>
        <Stat value="101->52" label="Elements" tone="warning" />
        <Stat value="1" label="SC Tab" />
        <Stat value="5->4" label="WS Panels" tone="success" />
        <Stat value="4->2" label="Settings" />
        <Stat value="10->7" label="Flows" tone="info" />
      </Grid>

      <Row gap={4} wrap>
        {tabLabels.map((t, i) => (
          <Tag key={i} active={tab === i} onClick={() => setTab(i)}>{t}</Tag>
        ))}
      </Row>

      <Divider />

      {tab === 0 && (
        <Stack gap={16}>
          <H2>Smart Copilot (v3) -- 极简版</H2>
          <Text tone="secondary" size="small">双击右键唤起，占屏幕 35x45%。Header 极简化（仅 Selection + 翻译/设置）。对话历史增强（复制/应用/来源跳转）。输入框简化。</Text>

          <Card>
            <CardHeader title="Smart Copilot" trailing={<Pill tone="info">35% x 45% 屏幕</Pill>} />
            <CardBody>
              <Stack gap={12}>
                <Row gap={6} align="center">
                  <Pill tone="primary">Selection</Pill>
                  <Spacer />
                  <Button variant="ghost">翻译</Button>
                  <Button variant="ghost" onClick={() => setTab(3)}>设置</Button>
                </Row>
                <Divider />
                <Card size="sm">
                  <CardBody>
                    <Stack gap={12}>
                      <Row justify="end"><Text style={{ maxWidth: "80%" }}>这个 Q2 的数据对吗？</Text></Row>
                      <Stack gap={4}>
                        <Text>Q2 营收 3800 万，与 Excel 原始数据一致。</Text>
                        <Text size="small" tone="secondary">q2_sales_data.xlsx 第 15 行</Text>
                        <Row gap={6}><Button variant="ghost">复制</Button><Button variant="ghost">应用</Button></Row>
                      </Stack>
                      <Row justify="end"><Text style={{ maxWidth: "80%" }}>利润率呢？</Text></Row>
                      <Stack gap={4}>
                        <Text>根据成本数据计算，Q2 利润率为 23.7%，较 Q1 提升 2.1 个百分点。</Text>
                        <Row gap={6}><Button variant="ghost">复制</Button><Button variant="ghost">应用</Button></Row>
                      </Stack>
                    </Stack>
                  </CardBody>
                </Card>
                <Divider />
                <Row gap={8} align="center">
                  <Text tone="secondary" style={{ flex: 1 }}>问点什么...</Text>
                  <Button variant="primary">发送</Button>
                </Row>
              </Stack>
            </CardBody>
          </Card>

          <Grid columns={3} gap={12}>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">1. Header 极简</Text><Text size="small" tone="secondary">仅保留 Selection 指示器 + 翻译/设置两个 icon。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">2. 对话历史增强</Text><Text size="small" tone="secondary">AI 回复下方添加 复制/应用 操作按钮。来源信息可点击跳转。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">3. 输入框简化</Text><Text size="small" tone="secondary">placeholder 简化为"问点什么..."。</Text></Stack></CardBody></Card>
          </Grid>
        </Stack>
      )}

      {tab === 1 && (
        <Stack gap={16}>
          <H2>Agent Workspace -- 4 Panel 工作台</H2>
          <Text tone="secondary" size="small">三击右键唤起，占屏幕 60x65%。精简为 Task / Chat / Files / Memory，Settings 删除。</Text>

          <Card>
            <CardHeader title="Agent Workspace" trailing={<Pill tone="info">60% x 65% 屏幕</Pill>} />
            <CardBody>
              <Row gap={0} style={{ minHeight: 340 }}>
                <Stack gap={0} style={{ width: 160, borderRight: `1px solid ${tokens.stroke.tertiary}`, padding: "12px 0" }}>
                  {["Task", "Chat", "Files", "Memory"].map((name, i) => (
                    <Tag key={i} active={wsPanel === i} onClick={() => setWsPanel(i)}>{name}</Tag>
                  ))}
                  <Spacer />
                  <Tag onClick={() => setTab(3)}>Settings</Tag>
                </Stack>
                <Stack gap={12} style={{ flex: 1, padding: 16 }}>
                  <Text weight="bold">Task: Quarterly Report Analysis</Text>
                  <Row gap={6}>
                    <Pill tone="success">Active</Pill>
                    <Pill>Template: Report</Pill>
                  </Row>
                  <Card size="sm"><CardBody>
                    <Text size="small" tone="secondary">Task Description</Text>
                    <Text size="small">Analyze Q2 data across all departments and produce a summary presentation.</Text>
                  </CardBody></Card>
                  <Table
                    headers={["File", "Size", "Action"]}
                    rows={[
                      ["q2_sales_data.xlsx", "2.4 MB", "Send"],
                      ["department_notes.md", "12 KB", "Send"],
                      ["prev_report.pptx", "890 KB", "Send"],
                    ]}
                  />
                </Stack>
              </Row>
            </CardBody>
          </Card>

          <H3>意图路由 UI (Chat 面板)</H3>
          <Card>
            <CardHeader title="Chat Intent Router" trailing={<Pill tone="info">Auto + 8 意图</Pill>} />
            <CardBody>
              <Stack gap={16}>
                <Text weight="semibold">意图选择器</Text>
                <Row gap={6} wrap>
                  {["Auto", "Chat", "Research", "PPT", "Translate", "Explain", "Fix", "Polish", "Review"].map((label, i) => (
                    <Tag key={i} active={intent === i} onClick={() => setIntent(i)}>{label}</Tag>
                  ))}
                </Row>
                <Card size="sm"><CardBody>
                  <Stack gap={8}>
                    <Text weight="semibold">Auto 模式检测结果</Text>
                    <Grid columns={3} gap={12}>
                      <Stack gap={2}><Text size="small" tone="secondary">识别意图</Text><Text weight="bold">PPT</Text></Stack>
                      <Stack gap={2}><Text size="small" tone="secondary">置信度</Text><Text weight="bold">92%</Text></Stack>
                      <Stack gap={2}><Text size="small" tone="secondary">命中词</Text><Pill tone="warning">共创、PPT、演示</Pill></Stack>
                    </Grid>
                  </Stack>
                </CardBody></Card>
                <Text size="small" tone="secondary">PPT → context_meta[ppt_mode=True] | Research → enable_web_search=True</Text>
              </Stack>
            </CardBody>
          </Card>

          <Grid columns={3} gap={12}>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">1. 稳定导航</Text><Text size="small" tone="secondary">左侧 Sidebar 始终可见: Task / Chat / Files / Memory。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">2. 任务锚点</Text><Text size="small" tone="secondary">Task 面板是 Chat / Files / Memory 的共同锚点。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">3. Settings 删除</Text><Text size="small" tone="secondary">Workspace Settings Panel 删除，改为 sidebar 齿轮直接弹 Settings Dialog。</Text></Stack></CardBody></Card>
          </Grid>
        </Stack>
      )}

      {tab === 2 && (
        <Stack gap={16}>
          <H2>V5Plus CoCreation -- 核心动线</H2>
          <Text tone="secondary" size="small">输入原文 → 生成PPT → 编辑PPT → 导出PPT。IDE式窗口：占屏幕 70-80%，自适应分辨率。</Text>

          <Row gap={6}>
            {stageLabels.map((s, i) => (
              <Tag key={i} active={v5Stage === i} onClick={() => setV5Stage(i)}>{s}</Tag>
            ))}
          </Row>

          {v5Stage === 0 && (
            <Card>
              <CardHeader title="V5Plus CoCreation" trailing={<Pill tone="info">45x50% | Stage 1</Pill>} />
              <CardBody>
                <Stack gap={16}>
                  <Callout tone="info">有文本时自动跳过，直接进入 Stage 2</Callout>
                  <Text weight="bold">粘贴原文</Text>
                  <Text tone="secondary">粘贴文档内容...</Text>
                  <Row justify="space-between" align="center">
                    <Text size="small" tone="secondary">已输入 2,847 字</Text>
                    <Button variant="primary" onClick={() => setV5Stage(1)}>生成 PPT →</Button>
                  </Row>
                </Stack>
              </CardBody>
            </Card>
          )}

          {v5Stage === 1 && (
            <Card>
              <CardHeader title="V5Plus - 生成" trailing={<Pill tone="info">60x60% | Stage 2</Pill>} />
              <CardBody>
                <Stack gap={16}>
                  <Row gap={8} align="center">
                    <Text weight="bold">文档分析</Text>
                    <Pill tone="info">技术方案</Pill>
                    <Text size="small" tone="secondary">2,847 字 / 6 段</Text>
                  </Row>
                  <Stack gap={8}>
                    <Row gap={6} align="center" onClick={() => setShowStrat((p) => !p)} style={{ cursor: "pointer" }}>
                      <Text size="small" tone="secondary">{showStrat ? "▼" : "▶"} 策略（可选）</Text>
                    </Row>
                    {showStrat && (
                      <Text size="small">
                        <Text weight="semibold">推荐：金字塔式</Text>
                        <Text tone="secondary"> 结论先行，数据支撑</Text>
                      </Text>
                    )}
                  </Stack>
                  <Row justify="end">
                    <Button variant="primary" onClick={() => setV5Stage(2)}>开始生成 →</Button>
                  </Row>
                </Stack>
              </CardBody>
            </Card>
          )}

          {v5Stage === 2 && (
            <Card>
              <CardHeader title="V5Plus - 编辑导出" trailing={<Pill tone="info">80x80% | Stage 3</Pill>} />
              <CardBody>
                <Stack gap={12}>
                  <Grid columns={2} gap={12}>
                    <Stack gap={8}>
                      <Text weight="semibold">PPT 预览区 (60%)</Text>
                      <Card size="sm"><CardBody>
                        <Stack gap={8}>
                          <Text weight="bold">{["封面", "核心结论", "三大支撑", "数据对比", "执行计划", "Q&A"][selSlide]}</Text>
                          <Row gap={4}>
                            {[0,1,2,3,4,5].map(i => (
                              <Tag key={i} active={selSlide === i} onClick={() => setSelSlide(i)} size="sm">{String(i+1)}</Tag>
                            ))}
                          </Row>
                          {!aiDiffAccepted && selSlide === 0 && (
                            <Callout tone="info">
                              <Stack gap={6}>
                                <Text size="small" weight="semibold">AI 建议修改标题</Text>
                                <Row gap={6}>
                                  <Button variant="primary" onClick={() => setAiDiffAccepted(true)}>接受</Button>
                                  <Button variant="ghost" onClick={() => setAiDiffAccepted(true)}>拒绝</Button>
                                </Row>
                              </Stack>
                            </Callout>
                          )}
                        </Stack>
                      </CardBody></Card>
                      <Row gap={4} wrap>
                        {["center", "text", "3-col", "chart", "timeline"].map(l => (
                          <Tag key={l} size="sm">{l}</Tag>
                        ))}
                      </Row>
                    </Stack>
                    <Stack gap={8}>
                      <Text weight="semibold">原文区 (40%)</Text>
                      <Card size="sm"><CardBody>
                        <Stack gap={8}>
                          {[
                            { text: "2026年，智能体技术在多个领域取得了突破性进展...", slide: "S2" },
                            { text: "以下是我们对本年度发展的全面回顾...", slide: "+" },
                            { text: "多模态感知能力的提升是最显著的突破之一...", slide: "S3" },
                            { text: "端侧本地化部署降低了延迟...", slide: "S4" },
                          ].map((p, i) => (
                            <Row key={i} gap={6} align="start">
                              <Text size="small" style={{ flex: 1 }}>{p.text}</Text>
                              <Tag size="sm">{p.slide}</Tag>
                            </Row>
                          ))}
                        </Stack>
                      </CardBody></Card>
                      <Row gap={6} align="center">
                        <Text tone="secondary" style={{ flex: 1 }}>输入指令：改标题、调版式...</Text>
                        <Button variant="primary">发送</Button>
                      </Row>
                    </Stack>
                  </Grid>
                  <Divider />
                  <Row justify="end">
                    <Button variant="primary">导出 PPT</Button>
                  </Row>
                </Stack>
              </CardBody>
            </Card>
          )}

          <H3>多表达方式选择器</H3>
          <Card>
            <CardHeader title="表达方式选择" trailing={<Pill>6 种模式</Pill>} />
            <CardBody>
              <Grid columns={3} gap={8}>
                {[
                  { name: "纯文本", desc: "文字为主" },
                  { name: "图文混排", desc: "图片+文字" },
                  { name: "表格", desc: "数据表格" },
                  { name: "图表", desc: "柱状/饼图" },
                  { name: "流程图", desc: "流程/时间线" },
                  { name: "三栏布局", desc: "并列展示" },
                ].map((mode, i) => (
                  <Card key={i} size="sm"><CardBody>
                    <Stack gap={2}>
                      <Text weight="semibold">{mode.name}</Text>
                      <Text size="small" tone="secondary">{mode.desc}</Text>
                    </Stack>
                  </CardBody></Card>
                ))}
              </Grid>
              <Text size="small" tone="secondary">选择后 AI 将自动调整幻灯片布局和内容组织方式</Text>
            </CardBody>
          </Card>

          <Grid columns={3} gap={12}>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">1. IDE式窗口</Text><Text size="small" tone="secondary">Stage 1:45x50% | Stage 2:60x60% | Stage 3:80x80%</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">2. Stage 2 推荐生成</Text><Text size="small" tone="secondary">文档分析 + 推荐策略（默认金字塔）。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">3. Stage 3 编辑导出</Text><Text size="small" tone="secondary">60/40 布局：中间 PPT + 右侧原文。Click-to-Edit + AI Diff。</Text></Stack></CardBody></Card>
          </Grid>
        </Stack>
      )}

      {tab === 3 && (
        <Stack gap={16}>
          <H2>Settings Dialog -- 分层引擎</H2>
          <Text tone="secondary" size="small">2 入口: SC Header + WS Sidebar (齿轮)。占屏幕 45x55%。Engine 分 Basic + Advanced 折叠。</Text>

          <Card>
            <CardHeader title="Settings" trailing={<Pill tone="info">45% x 55% 屏幕</Pill>} />
            <CardBody>
              <Row gap={0} style={{ minHeight: 360 }}>
                <Stack gap={0} style={{ width: 120, borderRight: `1px solid ${tokens.stroke.tertiary}`, padding: "12px 0" }}>
                  {["Engine", "Appearance", "Shortcuts", "Advanced"].map((s, i) => (
                    <Tag key={i} active={settingsSection === i} onClick={() => setSettingsSection(i)}>{s}</Tag>
                  ))}
                </Stack>
                <Stack gap={16} style={{ flex: 1, padding: "16px 20px" }}>
                  <Text weight="bold">Appearance Settings</Text>
                  <Stack gap={8}>
                    <Text weight="semibold" size="small">Smart Copilot 显示元素</Text>
                    {[
                      { key: "sourceChips", label: "S/D/C/F/B Source chips" },
                      { key: "wordCount", label: "字数统计" },
                      { key: "persona", label: "角色选择器" },
                      { key: "closeBtn", label: "关闭按钮" },
                    ].map((item) => (
                      <Row key={item.key} justify="space-between" align="center">
                        <Text size="small">{item.label}</Text>
                        <Switch checked={toggles[item.key as keyof typeof toggles]} onChange={() => toggleItem(item.key)} />
                      </Row>
                    ))}
                  </Stack>
                  <Divider />
                  <Stack gap={8}>
                    <Text weight="semibold" size="small">快捷功能标签</Text>
                    {[
                      { key: "explain", label: "Explain" },
                      { key: "summarize", label: "Summarize" },
                      { key: "polish", label: "Polish" },
                      { key: "revise", label: "修订" },
                    ].map((item) => (
                      <Row key={item.key} justify="space-between" align="center">
                        <Text size="small">{item.label}</Text>
                        <Switch checked={toggles[item.key as keyof typeof toggles]} onChange={() => toggleItem(item.key)} />
                      </Row>
                    ))}
                  </Stack>
                  <Divider />
                  <Stack gap={4}>
                    <Text size="small" tone="secondary">Theme</Text>
                    <Row gap={8}>
                      {["Dark", "Light", "Auto"].map((t, i) => (
                        <Tag key={i} active={theme === i} onClick={() => setTheme(i)}>{t}</Tag>
                      ))}
                    </Row>
                  </Stack>
                </Stack>
              </Row>
            </CardBody>
          </Card>

          <H3>Skill 体系 UI</H3>
          <Grid columns={2} gap={12}>
            <Card>
              <CardHeader title="Skill Panel" trailing={<Pill>Sidebar 集成</Pill>} />
              <CardBody>
                <Table
                  headers={["Skill", "Status", "Action"]}
                  rows={[
                    ["PPT Generator", "Active", "配置"],
                    ["Translator", "Active", "配置"],
                    ["Research", "Inactive", "配置"],
                    ["Code Review", "Inactive", "配置"],
                  ]}
                />
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Skill Search" trailing={<Pill>Cmd+K</Pill>} />
              <CardBody>
                <Stack gap={12}>
                  <Text tone="secondary">搜索 Skills...</Text>
                  <Text weight="semibold" size="small">最近使用</Text>
                  {["PPT Generator - 生成演示文稿", "Translator - 多语言翻译", "Research - 联网调研"].map((r, i) => (
                    <Card key={i} size="sm"><CardBody>
                      <Text size="small">{r.split(" - ")[0]}</Text>
                      <Text size="small" tone="secondary">{r.split(" - ")[1]}</Text>
                    </CardBody></Card>
                  ))}
                </Stack>
              </CardBody>
            </Card>
          </Grid>

          <Grid columns={3} gap={12}>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">1. 入口收敛</Text><Text size="small" tone="secondary">3-4 入口 -> 2 (SC Header + WS Sidebar 齿轮)。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">2. UI 元素可配置</Text><Text size="small" tone="secondary">Smart Copilot 显示元素和快捷标签默认隐藏，可通过设置开启。</Text></Stack></CardBody></Card>
            <Card size="sm"><CardBody><Stack gap={4}><Text weight="semibold">3. 主题迁移</Text><Text size="small" tone="secondary">原 Studio 底部 4 主题按钮移至 Settings Appearance。</Text></Stack></CardBody></Card>
          </Grid>
        </Stack>
      )}

      {tab === 4 && (
        <Stack gap={16}>
          <H2>Navigation Flows and Window Hierarchy</H2>
          <Text tone="secondary" size="small">核心原则: 每条链路必须高频且必要。删除低频跨窗跳转。</Text>

          <Card>
            <CardHeader title="Window Hierarchy" trailing={<Pill>Level 0-3</Pill>} />
            <CardBody>
              <Stack gap={6}>
                {[
                  { level: 0, label: "System Tray", desc: "Always on, menu bar icon", color: "neutral" },
                  { level: 1, label: "Smart Copilot", desc: "Double right-click | 35x45%", color: "primary" },
                  { level: 2, label: "Workspace", desc: "Triple right-click | 60x65%", color: "success" },
                  { level: 2, label: "V5Plus CoCreate", desc: "Input CoCreate | IDE window | Stage", color: "warning" },
                  { level: 3, label: "Settings Dialog", desc: "SC/WS gear icon | Modal | 45x55%", color: "info" },
                ].map((w, i) => (
                  <Row key={i} gap={10} align="center" style={{ marginLeft: w.level * 24 }}>
                    <Pill tone={w.color as any}>{w.label}</Pill>
                    <Text size="small" tone="secondary">{w.desc}</Text>
                  </Row>
                ))}
              </Stack>
            </CardBody>
          </Card>

          <H3>Navigation Flow Matrix</H3>
          <Table
            headers={["ID", "From -> To", "Trigger", "Keep?", "Rationale"]}
            rows={[
              ["F1", "SC Work <-> Chat", "Tab click", "Yes", "Core tab switch"],
              ["F2", "SC -> V5Plus CoCreate", "Input CoCreate", "Yes", "PPT entry"],
              ["F3", "SC -> Settings Dialog", "Header gear", "Yes", "Settings entry"],
              ["F4", "WS -> Settings Dialog", "Sidebar gear", "Yes", "Settings entry"],
              ["F5", "Work -> Chat (result)", "Inline prompt", "Yes", "Natural flow"],
              ["F6", "Chat -> V5Plus", "Send to CoCreate", "Yes", "Chat -> PPT"],
              ["F7", "Tray -> SC / WS", "Right-click", "Yes", "Main entry"],
              ["F8", "V5Plus -> SC Chat", "After export", "Del", "Low freq"],
              ["F9", "CoCreation -> SC", "Stage 3 jump", "Del", "Low freq"],
              ["F10", "WS Settings -> Dialog", "Config btn", "Del", "Redundant layer"],
            ]}
            rowTone={(row, i) => {
              const id = (row as any)[0];
              return id && id.startsWith("F") && parseInt(id.slice(1)) >= 8 ? "danger" : "default";
            }}
          />

          <H3>Chat Unification</H3>
          <Grid columns={2} gap={12}>
            <Card>
              <CardHeader title="Before: 2 Isolated Chats" trailing={<Pill tone="danger">Problem</Pill>} />
              <CardBody>
                <Grid columns={2} gap={12}>
                  <Card size="sm"><CardBody>
                    <Text weight="semibold" size="small">SC Chat Tab</Text>
                    <Text size="small" tone="secondary">Bubble UI / session A / No actions</Text>
                  </CardBody></Card>
                  <Card size="sm"><CardBody>
                    <Text weight="semibold" size="small">WS Chat Panel</Text>
                    <Text size="small" tone="secondary">Plain HTML / session B / 9 actions</Text>
                  </CardBody></Card>
                </Grid>
                <Callout tone="danger">NOT connected</Callout>
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="After: 1 Unified ChatWidget" trailing={<Pill tone="success">Solution</Pill>} />
              <CardBody>
                <Grid columns={2} gap={12}>
                  <Card size="sm"><CardBody>
                    <Text weight="semibold" size="small">SC Chat Tab</Text>
                    <Text size="small" tone="secondary">ChatWidget</Text>
                  </CardBody></Card>
                  <Card size="sm"><CardBody>
                    <Text weight="semibold" size="small">WS Chat Panel</Text>
                    <Text size="small" tone="secondary">ChatWidget</Text>
                  </CardBody></Card>
                </Grid>
                <Callout tone="success">Shared session + history + actions</Callout>
                <Text size="small" tone="secondary">Bubble UI + action routing + shared session</Text>
              </CardBody>
            </Card>
          </Grid>

          <Grid columns={4} gap={16}>
            <Stat value="101+" label="Current Elements" tone="warning" />
            <Stat value="~52" label="Target Elements" tone="success" />
            <Stat value="-48%" label="Reduction" />
            <Stat value="10->7" label="Nav Flows" />
          </Grid>
        </Stack>
      )}

      <Spacer />
    </Stack>
  );
}
