"""
Content-First 4 阶段 PPT 生成管线

阶段 1: Topic Extraction   - 从原文提取核心主题
阶段 2: Content Mapping    - 每主题生成要点和预估页数
阶段 3: Format Selection   - 根据内容类型选择图表/表格/流程图/文本
阶段 4: Slide Assembly     - 组装完整 slides JSON（仅负责排版）

设计原则：
- 每阶段输出可度量、可校验的中间结果，消除单次 LLM 调用的质量波动
- 阶段间通过 clean JSON 传递，不依赖 LLM 的上下文记忆
- 每个阶段独立可重试，失败不污染其他阶段
"""

import json
import re
import time
import uuid
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Topic:
    title: str
    abstract: str
    importance_rank: int = 1


@dataclass
class ContentItem:
    text: str
    level: int = 0
    content_type: str = "text"


@dataclass
class ContentMapping:
    topic_index: int
    topic_title: str
    items: List[ContentItem] = field(default_factory=list)
    estimated_pages: int = 1


@dataclass
class FormatResult:
    item_index: int
    content_type: str = "text"
    chart_type: Optional[str] = None
    chart_data: Optional[dict] = None
    table_data: Optional[dict] = None
    flowchart_data: Optional[dict] = None
    confidence: float = 0.5
    source: str = "regex"


@dataclass
class PipelineResult:
    slides: list
    topics: List[Topic]
    content_mappings: List[ContentMapping]
    format_results: List[List[FormatResult]]
    total_pages: int
    stage_durations: Dict[str, float] = field(default_factory=dict)


class PPTGenerationPipeline:
    """Content-First 4 阶段 PPT 生成管线"""

    MAX_TOPICS = 8
    MIN_TOPICS = 2
    MAX_ITEMS_PER_TOPIC = 6
    MAX_ITEMS_PER_SLIDE = 6

    def __init__(self, progress_callback: Optional[Callable] = None):
        self._progress = progress_callback or (lambda s, p, m: None)
        self._stage_durations = {}

    def run(self, text: str) -> PipelineResult:
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")
        self._stage_durations = {}
        self._report_progress("准备中", 0, "开始分析文档...")

        topics = self._run_stage("TopicExtract", self._extract_topics, text, progress_pct=10)
        mappings = self._run_stage("ContentMap", self._map_content, topics, text, progress_pct=25)
        format_results = self._run_stage("FormatSelect", self._select_formats, mappings, None, progress_pct=55)
        slides = self._run_stage("SlideAssembly", self._assemble_slides, mappings, format_results, progress_pct=80)

        self._report_progress("完成", 100, f"生成完成，共 {len(slides)} 页")
        return PipelineResult(
            slides=slides, topics=topics, content_mappings=mappings,
            format_results=format_results, total_pages=len(slides),
            stage_durations=self._stage_durations,
        )

    def _run_stage(self, name: str, fn: Callable, *args, progress_pct: int = 50, progress_max: int = 100) -> Any:
        t0 = time.time()
        self._report_progress(name, progress_pct, f"{name}...")
        result = fn(*args)
        self._stage_durations[name] = time.time() - t0
        return result

    def _report_progress(self, stage: str, pct: int, msg: str):
        try:
            self._progress(stage, pct, msg)
        except Exception:
            pass

    # ---- 阶段 1: Topic Extraction ----
    def _extract_topics(self, text: str) -> List[Topic]:
        self._report_progress("阶段1", 5, "分析文档结构...")

        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            sid = f"ppt_topic_{uuid.uuid4().hex[:8]}"
            t0 = time.time()
            obs.gui_log(f"PPT Topic Extract START | text_len={len(text)}", session_id=sid, event="PPT_TOPIC_EXTRACT_START")

            full = ""
            for chunk in call_agent_pipeline_sync(text=text, action_type="ppt", session_id=sid,
                                                  context_source="ppt_topic_extract", is_new_task=True):
                full += chunk

            elapsed = (time.time() - t0) * 1000
            obs.gui_log(f"PPT Topic Extract DONE", session_id=sid, event="PPT_TOPIC_EXTRACT_DONE", elapsed_ms=elapsed)
            topics = self._parse_topics(full)
            if topics and len(topics) >= self.MIN_TOPICS:
                return topics

            # retry
            sid2 = f"ppt_topic_r_{uuid.uuid4().hex[:8]}"
            full = ""
            for chunk in call_agent_pipeline_sync(text=text, action_type="ppt", session_id=sid2,
                                                  context_source="ppt_topic_extract", is_new_task=True):
                full += chunk
            topics = self._parse_topics(full)
            if topics and len(topics) >= self.MIN_TOPICS:
                return topics
            obs.gui_log("PPT Topic Extract FALLBACK", session_id=sid, event="PPT_VALIDATION_FAIL",
                        level="WARN", data_json=json.dumps({"reason": "insufficient_topics"}))
            return self._fallback_topics(text)
        except Exception as e:
            logger.error(f"阶段1失败: {e}")
            return self._fallback_topics(text)

    def _parse_topics(self, raw: str) -> Optional[List[Topic]]:
        try:
            m = re.search(r'\[.*\]', self._clean(raw), re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                topics = []
                for d in data:
                    if isinstance(d, dict) and d.get("title"):
                        topics.append(Topic(title=str(d["title"]),
                                           abstract=str(d.get("abstract", "")),
                                           importance_rank=int(d.get("importance_rank", len(topics)+1))))
                return topics or None
        except Exception:
            pass
        return None

    def _fallback_topics(self, text: str) -> List[Topic]:
        paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        topics = []
        for i, p in enumerate(paras[:self.MAX_TOPICS]):
            title = (p.split('\n')[0].strip('# -•') or f"主题{i+1}")[:60]
            topics.append(Topic(title=title, abstract=p[:100], importance_rank=i+1))
        return topics[:self.MAX_TOPICS]

    # ---- 阶段 2: Content Mapping ----
    def _map_content(self, topics: List[Topic], text: str) -> List[ContentMapping]:
        self._report_progress("阶段2", 22, f"{len(topics)}个主题内容映射...")
        mappings = []
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            for i, topic in enumerate(topics[:self.MAX_TOPICS]):
                self._report_progress("阶段2", 22 + int(28*i/max(len(topics),1)), f"映射: {topic.title}")
                sid = f"ppt_map_{uuid.uuid4().hex[:8]}"
                t0 = time.time()
                prompt = json.dumps({"topic_index": i, "title": topic.title, "abstract": topic.abstract,
                                     "source_text_hint": text[:500]}, ensure_ascii=False)
                obs.gui_log(f"PPT Content Map START", session_id=sid, event="PPT_CONTENT_MAP_START")
                full = ""
                for chunk in call_agent_pipeline_sync(text=prompt, action_type="ppt", session_id=sid,
                                                      context_source="ppt_content_map", is_new_task=True):
                    full += chunk
                elapsed = (time.time() - t0) * 1000
                obs.gui_log(f"PPT Content Map DONE", session_id=sid, event="PPT_CONTENT_MAP_DONE", elapsed_ms=elapsed)
                mapping = self._parse_mapping(full, i, topic.title)
                mappings.append(mapping or self._fallback_mapping(i, topic))
        except Exception as e:
            logger.error(f"阶段2失败: {e}")
            for i, topic in enumerate(topics[:self.MAX_TOPICS]):
                if i >= len(mappings):
                    mappings.append(self._fallback_mapping(i, topic))
        return mappings

    def _parse_mapping(self, raw: str, idx: int, title: str) -> Optional[ContentMapping]:
        try:
            m = re.search(r'\{.*\}', self._clean(raw), re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                items = [ContentItem(text=str(x["text"]), level=int(x.get("level",0)),
                                     content_type=str(x.get("content_type","text")))
                         for x in d.get("items", []) if isinstance(x, dict) and x.get("text")]
                if items:
                    return ContentMapping(topic_index=idx, topic_title=title,
                                         items=items[:self.MAX_ITEMS_PER_TOPIC],
                                         estimated_pages=max(1, int(d.get("estimated_pages",1))))
        except Exception:
            pass
        return None

    def _fallback_mapping(self, idx: int, topic: Topic) -> ContentMapping:
        return ContentMapping(topic_index=idx, topic_title=topic.title,
                             items=[ContentItem(text=topic.title, level=0),
                                    ContentItem(text=topic.abstract[:100], level=1)])

    # ---- 阶段 3: Format Selection ----
    def _select_formats(self, mappings: List[ContentMapping], _) -> List[List[FormatResult]]:
        self._report_progress("阶段3", 52, "分析内容类型...")
        from .content_converter import TextAnalyzer
        all_results = []
        for m_idx, mapping in enumerate(mappings):
            self._report_progress("阶段3", 52+int(10*m_idx/max(len(mappings),1)), f"格式: {mapping.topic_title}")
            page_results = []
            for i_idx, item in enumerate(mapping.items):
                analysis = TextAnalyzer.analyze(item.text)
                best = analysis.get("best_match")
                if best:
                    ctype = best.get("type", "text")
                    conf = best.get("confidence", 0.5)
                    result = FormatResult(item_index=i_idx, confidence=conf, source="regex")
                    if ctype == "chart":
                        result.content_type = "chart"
                        result.chart_type = best.get("subtype", "bar")
                        ed = analysis.get("extracted_data")
                        if ed:
                            result.chart_data = {"labels": ed.get("labels",[]),
                                                  "datasets": ed.get("datasets",[]),
                                                  "title": mapping.topic_title}
                        if conf < 0.7:
                            result = self._llm_confirm(result, item.text, mapping.topic_title)
                    elif ctype == "table":
                        result.content_type = "table"
                        ed = analysis.get("extracted_data")
                        if ed:
                            result.table_data = ed
                    elif ctype == "flowchart":
                        result.content_type = "flowchart"
                        ed = analysis.get("extracted_data")
                        if ed:
                            result.flowchart_data = ed
                    else:
                        result.content_type = "text"
                    page_results.append(result)
                else:
                    page_results.append(FormatResult(item_index=i_idx, content_type="text", confidence=0.9))
            # 限流: 每页特殊类型≤2
            sp = sum(1 for r in page_results if r.content_type != "text")
            if sp > 2:
                for r in page_results:
                    if r.content_type != "text" and sp > 2:
                        r.content_type = "text"; r.chart_data = None; r.table_data = None; r.source = "fallback"; sp -= 1
            all_results.append(page_results)
        return all_results

    def _llm_confirm(self, result: FormatResult, text: str, topic_title: str) -> FormatResult:
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability
            obs = PipelineObservability.get_instance()
            sid = f"ppt_fmt_{uuid.uuid4().hex[:8]}"
            t0 = time.time()
            prompt = json.dumps({"text": text, "suggested_type": result.chart_type or result.content_type,
                                 "topic": topic_title}, ensure_ascii=False)
            obs.gui_log("PPT Chart Convert START", session_id=sid, event="PPT_CHART_CONVERT_START")
            full = ""
            for chunk in call_agent_pipeline_sync(text=prompt, action_type="ppt", session_id=sid,
                                                  context_source="ppt_chart_convert", is_new_task=True):
                full += chunk
            elapsed = (time.time() - t0) * 1000
            obs.gui_log("PPT Chart Convert DONE", session_id=sid, event="PPT_CHART_CONVERT_DONE", elapsed_ms=elapsed)
            parsed = self._parse_chart(full)
            if parsed and parsed.get("content_type"):
                result.content_type = parsed["content_type"]
                result.chart_type = parsed.get("chart_type", "bar")
                result.chart_data = parsed.get("chart_data")
                result.table_data = parsed.get("table_data")
                result.source = "llm"
                result.confidence = 0.85
            else:
                obs.gui_log("PPT Chart Convert FAIL", session_id=sid, event="PPT_CHART_CONVERT_FAIL", level="WARN")
        except Exception as e:
            logger.warning(f"LLM格式确认失败: {e}")
        return result

    def _parse_chart(self, raw: str) -> Optional[dict]:
        try:
            m = re.search(r'\{.*\}', self._clean(raw), re.DOTALL)
            return json.loads(m.group(0)) if m else None
        except Exception:
            return None

    # ---- 阶段 4: Slide Assembly ----
    def _assemble_slides(self, mappings: List[ContentMapping],
                          format_results: List[List[FormatResult]]) -> list:
        self._report_progress("阶段4", 77, "组装幻灯片...")
        try:
            from opencopilot.agent.caller import call_agent_pipeline_sync
            from opencopilot.agent.observability import PipelineObservability

            assembly_input = []
            for m, fr_list in zip(mappings, format_results):
                items_data = []
                for item, fr in zip(m.items, fr_list):
                    d = {"text": item.text, "level": item.level, "content_type": fr.content_type}
                    if fr.chart_data:
                        d["chart_data"] = fr.chart_data; d["chart_type"] = fr.chart_type
                    if fr.table_data:
                        d["table_data"] = fr.table_data
                    if fr.flowchart_data:
                        d["flowchart_data"] = fr.flowchart_data
                    items_data.append(d)
                assembly_input.append({"topic_title": m.topic_title, "estimated_pages": m.estimated_pages, "items": items_data})

            obs = PipelineObservability.get_instance()
            sid = f"ppt_asm_{uuid.uuid4().hex[:8]}"
            prompt = json.dumps({"content_plan": assembly_input, "instruction": (
                "根据 content_plan 组装 PPT slides JSON 数组。每个 topic 按 estimated_pages 分页。"
                "保留已有的 content_type 不要改回 text。每页 items≤6。标题≤40字。"
                "必须包含封面页（type=title）和结尾页（type=ending, layout=center, title='谢谢'）。只输出JSON数组。"
            )}, ensure_ascii=False, indent=2)[:4000]

            self._report_progress("阶段4", 80, "AI排版中...")
            full = ""
            for chunk in call_agent_pipeline_sync(text=prompt, action_type="ppt", session_id=sid,
                                                  context_source="ppt_generator", is_new_task=True):
                full += chunk
            slides = self._parse_slides(full)
            return slides if (slides and len(slides) >= 2) else self._fallback_assemble(mappings, format_results)
        except Exception as e:
            logger.error(f"阶段4失败: {e}")
            return self._fallback_assemble(mappings, format_results)

    def _parse_slides(self, raw: str) -> Optional[list]:
        try:
            m = re.search(r'\[.*\]', self._clean(raw), re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else None
        except Exception:
            pass
        try:
            from ppt_generator import extract_json_from_text
            r = extract_json_from_text(self._clean(raw))
            if isinstance(r, list): return r
            if isinstance(r, dict) and "slides" in r: return r["slides"]
        except Exception:
            pass
        return None

    def _fallback_assemble(self, mappings: List[ContentMapping],
                            format_results: List[List[FormatResult]]) -> list:
        slides = []
        for m, fr_list in zip(mappings, format_results):
            for page_idx in range(m.estimated_pages):
                start = page_idx * self.MAX_ITEMS_PER_SLIDE
                end = start + self.MAX_ITEMS_PER_SLIDE
                if start >= len(m.items):
                    break
                items = []
                for item, fr in zip(m.items[start:end], fr_list[start:end]):
                    d = {"id": uuid.uuid4().hex[:8], "text": item.text, "level": item.level, "content_type": fr.content_type}
                    if fr.chart_data:
                        d["chart_data"] = fr.chart_data; d["chart_type"] = fr.chart_type
                    if fr.table_data:
                        d["table_data"] = fr.table_data
                    if fr.flowchart_data:
                        d["flowchart_data"] = fr.flowchart_data
                    items.append(d)
                title = f"{m.topic_title}（续{page_idx+1}）"[:40] if m.estimated_pages > 1 else m.topic_title[:40]
                slides.append({"id": uuid.uuid4().hex[:8], "type": "content", "layout":
                              "image_right" if any(fr.content_type in ("chart","table") for fr in fr_list[start:end]) else "text_only",
                              "title": title, "subtitle": "", "items": items})
        if slides:
            slides.insert(0, {"id": uuid.uuid4().hex[:8], "type": "title", "layout": "center",
                             "title": mappings[0].topic_title[:40] if mappings else "演示文稿", "subtitle": ""})
            slides.append({"id": uuid.uuid4().hex[:8], "type": "ending", "layout": "center",
                          "title": "谢谢", "subtitle": "Q & A"})
        return slides

    @staticmethod
    def _clean(raw: str) -> str:
        c = re.sub(r'<[^>]*>', '', raw)  # remove think tags
        c = re.sub(r'```\w*\s*', '', c)
        return c.replace('```', '')
