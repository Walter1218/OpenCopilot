"""Stage 2: 策略发现 — 修辞分析 + 叙事策略选择

纯正则驱动的文档结构分析（<500ms，不调用 LLM）。
提供 3 种叙事策略（金字塔/叙事/对比），Agent 推荐一种，用户可切换。
"""
import re
import time
import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QComboBox,
    QFrame, QButtonGroup, QRadioButton,
)

from gui.v5plus import tokens_plus as T
from gui.v5.telemetry import telemetry

logger = logging.getLogger(__name__)


# =============================================================================
# 修辞分析引擎（纯正则驱动）
# =============================================================================

# 段落类型检测正则
_PATTERNS = {
    "background": [
        r"(?:背景|现状|概述|引言|简介|前言|overview|background|introduction)",
        r"(?:随着|当前|目前|近年来|在.+领域)",
    ],
    "architecture": [
        r"(?:架构|框架|设计|方案|系统|structure|architecture|framework|design)",
        r"(?:模块|组件|层次|分层|组件|component|module|layer)",
    ],
    "data": [
        r"\d+\.?\d*\s*(?:%|％|倍|万|亿|GB|MB|KB|ms|秒|次|条|个)",
        r"(?:数据|统计|指标|报告|data|metric|statistic|report|percent)",
    ],
    "comparison": [
        r"(?:对比|比较|优劣|vs\.?|versus|compare|advantage|disadvantage)",
        r"(?:方案[A-Z一二三]|选项|选择|alternative|option)",
    ],
    "process": [
        r"(?:流程|步骤|阶段|第一步|step|phase|stage|process|workflow)",
        r"(?:首先.+然后.+最后|1\..+2\..+3\.)",
    ],
    "summary": [
        r"(?:总结|结论|展望|下一步|next step|conclusion|summary|future)",
        r"(?:综上|因此|所以|总之|in summary|in conclusion)",
    ],
    "intro": [
        r"(?:本文|本报告|本文档|this (?:document|report|paper))",
    ],
}

# 文档类型检测
_DOC_TYPE_RULES = [
    ("tech_proposal", r"(?:技术方案|解决方案|架构设计|technical proposal|solution)"),
    ("work_report", r"(?:工作报告|周报|月报|总结汇报|work report|weekly)"),
    ("product_intro", r"(?:产品介绍|产品说明|功能介绍|product|feature)"),
    ("research", r"(?:研究|论文|分析|research|paper|analysis)"),
    ("decision_doc", r"(?:决策|论证|选型|对比分析|decision|comparison)"),
]

_DOC_TYPE_LABELS = {
    "tech_proposal": "技术方案",
    "work_report": "工作报告",
    "product_intro": "产品介绍",
    "research": "研究报告",
    "decision_doc": "决策论证",
    "general": "通用文档",
}

# 文档类型 → 推荐策略
_DOC_TYPE_STRATEGY = {
    "tech_proposal": "narrative",
    "work_report": "pyramid",
    "product_intro": "narrative",
    "research": "pyramid",
    "decision_doc": "comparison",
    "general": "pyramid",
}


def analyze_text(text: str) -> dict:
    """纯前端修辞分析（<500ms，不调用 LLM）

    Returns:
        {
            "doc_type": str,
            "doc_type_label": str,
            "paragraph_count": int,
            "paragraph_types": [str, ...],
            "char_count": int,
            "data_density": float,  # 0.0~1.0
            "recommended_strategy": str,  # pyramid/narrative/comparison
            "elapsed_ms": float,
        }
    """
    t0 = time.monotonic()

    # 段落切分
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(raw_paragraphs) <= 1 and "\n" in text:
        raw_paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    # 段落类型标注
    paragraph_types = []
    for para in raw_paragraphs:
        detected = "other"
        for ptype, patterns in _PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, para, re.IGNORECASE):
                    detected = ptype
                    break
            if detected != "other":
                break
        paragraph_types.append(detected)

    # 文档类型检测
    doc_type = "general"
    for dtype, pattern in _DOC_TYPE_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            doc_type = dtype
            break

    # 数据密度（数字/百分比/比较词占总字符比例）
    data_matches = re.findall(r"\d+\.?\d*\s*(?:%|％|倍|万|亿|GB|MB|ms|秒|次)", text)
    comparison_words = re.findall(r"(?:对比|比较|优于|vs|versus|更)", text, re.IGNORECASE)
    data_density = min(1.0, (len(data_matches) + len(comparison_words)) / max(1, len(text) / 500))

    # 推荐策略
    recommended = _DOC_TYPE_STRATEGY.get(doc_type, "pyramid")

    elapsed_ms = (time.monotonic() - t0) * 1000

    return {
        "doc_type": doc_type,
        "doc_type_label": _DOC_TYPE_LABELS.get(doc_type, "通用文档"),
        "paragraph_count": len(raw_paragraphs),
        "paragraph_types": paragraph_types,
        "char_count": len(text),
        "data_density": round(data_density, 2),
        "recommended_strategy": recommended,
        "elapsed_ms": round(elapsed_ms, 1),
    }


# =============================================================================
# Stage 2 Widget
# =============================================================================

class StageStrategyWidget(QWidget):
    """Stage 2：策略发现"""

    # 信号：策略选定 + 开始生成
    submitted = pyqtSignal(dict)  # strategy_config
    # 信号：跳过策略，直接生成
    skipped = pyqtSignal(str)  # text

    def __init__(self, session_id: str = "", parent=None):
        super().__init__(parent)
        self._session_id = session_id
        self._text = ""
        self._analysis = None
        self._selected_strategy = "pyramid"
        self._strategy_group = QButtonGroup(self)
        self._strategy_buttons = {}
        self._init_ui()

    def _init_ui(self):
        # 去掉 QScrollArea，直接布局 — 避免需要滚动
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 20, 12)
        self._layout.setSpacing(8)

        # ── 标题 ──
        title_row = QHBoxLayout()
        icon = QLabel("🚦")
        icon.setStyleSheet(f"font-size: 20px; background: transparent; border: none;")
        title = QLabel("策略发现")
        title.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; background: transparent; border: none;"
        )
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        self._layout.addLayout(title_row)

        # ── 分析结果区（动态填充）──
        self._analysis_frame = QFrame()
        self._analysis_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.BG_ELEVATED};
                border-radius: 8px;
                border: 1px solid {T.STROKE_SUBTLE};
            }}
        """)
        self._analysis_layout = QVBoxLayout(self._analysis_frame)
        self._analysis_layout.setContentsMargins(14, 12, 14, 12)
        self._analysis_layout.setSpacing(8)

        self._doc_info_label = QLabel("等待文档分析...")
        self._doc_info_label.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: transparent; border: none;"
        )
        self._doc_info_label.setWordWrap(True)
        self._analysis_layout.addWidget(self._doc_info_label)

        # 段落类型热力图（动态填充）
        self._heatmap_row = QHBoxLayout()
        self._heatmap_row.setSpacing(3)
        self._analysis_layout.addLayout(self._heatmap_row)

        self._layout.addWidget(self._analysis_frame)

        # ── 策略选择区（标题 + 卡片 紧凑排列）──
        strategy_header = QLabel("选择叙事策略  <span style='color:#888;font-size:10px;'>Agent 推荐，可自由切换</span>")
        strategy_header.setTextFormat(Qt.TextFormat.RichText)
        strategy_header.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_BODY[0]}px; background: transparent; border: none;"
        )
        self._layout.addWidget(strategy_header)

        # 策略卡片
        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(10)
        for card in T.STRATEGY_CARDS:
            card_widget = self._create_strategy_card(card)
            self._cards_row.addWidget(card_widget)
        self._layout.addLayout(self._cards_row)

        # ── 可选配置 ──
        config_frame = QFrame()
        config_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(0, 8, 0, 0)
        config_layout.setSpacing(16)

        # 受众
        audience_label = QLabel("目标受众:")
        audience_label.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: transparent; border: none;"
        )
        config_layout.addWidget(audience_label)
        self._audience_input = QLineEdit()
        self._audience_input.setPlaceholderText("如：技术总监、产品经理")
        self._audience_input.setStyleSheet(self._input_style())
        self._audience_input.setMaximumWidth(220)
        config_layout.addWidget(self._audience_input)

        # 演讲时长
        duration_label = QLabel("演讲时长:")
        duration_label.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_BODY[0]}px; "
            f"background: transparent; border: none;"
        )
        config_layout.addWidget(duration_label)
        self._duration_combo = QComboBox()
        for val, label in T.DURATION_OPTIONS:
            self._duration_combo.addItem(label, val)
        self._duration_combo.setCurrentIndex(1)  # 默认 10 分钟
        self._duration_combo.setStyleSheet(self._combo_style())
        self._duration_combo.setMaximumWidth(120)
        config_layout.addWidget(self._duration_combo)

        config_layout.addStretch()
        self._layout.addWidget(config_frame)

        # ── 底部按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._skip_btn = QPushButton("跳过，直接生成")
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.setMinimumHeight(T.BTN_MEDIUM_HEIGHT)
        self._skip_btn.setStyleSheet(self._secondary_btn_style())
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)

        self._generate_btn = QPushButton("开始生成 →")
        self._generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._generate_btn.setMinimumHeight(T.BTN_MEDIUM_HEIGHT)
        self._generate_btn.setMinimumWidth(160)
        self._generate_btn.setStyleSheet(self._cta_btn_style())
        self._generate_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self._generate_btn)

        self._layout.addLayout(btn_row)

    # =========================================================================
    # 公共方法
    # =========================================================================

    def load_text(self, text: str):
        """加载原文并执行修辞分析"""
        self._text = text
        if not text or not text.strip():
            return

        # 执行分析
        self._analysis = analyze_text(text)

        telemetry().emit(
            "V5PLUS_STAGE2_ANALYSIS_DONE",
            session_id=self._session_id,
            elapsed_ms=self._analysis["elapsed_ms"],
            doc_type=self._analysis["doc_type"],
            paragraph_count=self._analysis["paragraph_count"],
            data_density=self._analysis["data_density"],
        )
        logger.info("Stage 2: analysis done in %.1fms — doc_type=%s, %d paragraphs",
                     self._analysis["elapsed_ms"],
                     self._analysis["doc_type"],
                     self._analysis["paragraph_count"])

        # 更新 UI
        self._update_analysis_display()

        # 设置推荐策略
        recommended = self._analysis["recommended_strategy"]
        self._select_strategy(recommended)

        telemetry().emit(
            "V5PLUS_STAGE2_STRATEGY_SELECT",
            session_id=self._session_id,
            strategy=recommended,
            is_recommended=True,
            source="auto",
        )

    def get_text(self) -> str:
        return self._text

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _update_analysis_display(self):
        """更新分析结果展示"""
        a = self._analysis
        if not a:
            return

        # 文档信息
        self._doc_info_label.setText(
            f"文档分析  [{a['doc_type_label']}]  "
            f"{a['char_count']:,} 字 / {a['paragraph_count']} 段  "
            f"（分析耗时 {a['elapsed_ms']:.0f}ms）"
        )
        self._doc_info_label.setStyleSheet(
            f"color: {T.TEXT_ACCENT}; font-size: {T.FONT_BODY[0]}px; "
            f"font-weight: bold; background: transparent; border: none;"
        )

        # 清空并重建热力图
        while self._heatmap_row.count():
            item = self._heatmap_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, ptype in enumerate(a["paragraph_types"]):
            color = T.PARAGRAPH_TYPE_COLORS.get(ptype, T.PARAGRAPH_TYPE_COLORS["other"])
            # 段落标题截取
            label_text = ptype[:2]
            chip = QLabel(label_text)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setFixedHeight(22)
            chip.setMinimumWidth(30)
            chip.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: #fff;
                    font-size: {T.FONT_TINY[0]}px;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
            """)
            chip.setToolTip(f"段落 {i + 1}: {ptype}")
            self._heatmap_row.addWidget(chip)
        self._heatmap_row.addStretch()

    def _create_strategy_card(self, card: dict) -> QFrame:
        """创建单个策略卡片"""
        frame = QFrame()
        frame.setFixedHeight(100)
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet(self._card_style(card["color"], selected=False))

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # 图标 + 标题
        top_row = QHBoxLayout()
        icon = QLabel(card["icon"])
        icon.setStyleSheet(
            f"font-size: 18px; color: {card['color']}; "
            f"background: transparent; border: none;"
        )
        label = QLabel(card["label"])
        label.setStyleSheet(
            f"color: {T.TEXT_PRIMARY}; font-weight: bold; "
            f"font-size: {T.FONT_HEADING[0]}px; background: transparent; border: none;"
        )
        top_row.addWidget(icon)
        top_row.addWidget(label)
        top_row.addStretch()

        # Radio 按钮
        radio = QRadioButton()
        radio.setStyleSheet(f"""
            QRadioButton::indicator {{
                width: 16px; height: 16px;
                border-radius: 8px;
                border: 2px solid {T.STROKE_BORDER};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {card['color']};
                background-color: {card['color']};
            }}
            QRadioButton {{
                background: transparent; border: none;
            }}
        """)
        self._strategy_group.addButton(radio)
        self._strategy_buttons[card["key"]] = (radio, frame, card["color"])
        radio.toggled.connect(
            lambda checked, key=card["key"]: self._on_strategy_toggled(key, checked)
        )
        top_row.addWidget(radio)
        layout.addLayout(top_row)

        # 副标题
        subtitle = QLabel(card["subtitle"])
        subtitle.setStyleSheet(
            f"color: {T.TEXT_SECONDARY}; font-size: {T.FONT_CAPTION[0]}px; "
            f"background: transparent; border: none;"
        )
        layout.addWidget(subtitle)

        # 模板
        template = QLabel(card["template"])
        template.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; font-size: {T.FONT_TINY[0]}px; "
            f"background: transparent; border: none;"
        )
        template.setWordWrap(True)
        layout.addWidget(template)

        # 编号结构列表（从 template 拆分，如 "核心结论 → 支撑论据 → 数据证据 → 下一步"）
        steps = [s.strip() for s in card["template"].split("→")]
        structure_label = QLabel(
            "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
        )
        structure_label.setStyleSheet(
            f"color: {card['color']}; font-size: {T.FONT_TINY[0]}px; "
            f"font-weight: 600; line-height: 1.5; "
            f"background: transparent; border: none; "
            f"padding: 4px 0;"
        )
        structure_label.setWordWrap(True)
        layout.addWidget(structure_label)

        # 点击卡片也可以选中
        frame.mousePressEvent = lambda e, key=card["key"]: self._select_strategy(key)

        return frame

    def _select_strategy(self, key: str):
        """程序化选中策略"""
        if key in self._strategy_buttons:
            radio, _, _ = self._strategy_buttons[key]
            radio.setChecked(True)

    def _on_strategy_toggled(self, key: str, checked: bool):
        """策略切换 → 更新卡片高亮"""
        if not checked:
            return

        old_strategy = self._selected_strategy
        self._selected_strategy = key

        # 更新所有卡片样式
        for k, (radio, frame, color) in self._strategy_buttons.items():
            is_selected = (k == key)
            frame.setStyleSheet(self._card_style(color, selected=is_selected))

        if old_strategy != key:
            telemetry().emit(
                "V5PLUS_STAGE2_STRATEGY_SELECT",
                session_id=self._session_id,
                strategy=key,
                is_recommended=(self._analysis and key == self._analysis["recommended_strategy"]),
                source="manual",
            )
            logger.info("Stage 2: strategy changed %s → %s", old_strategy, key)

    def _on_skip(self):
        """跳过策略发现，直接生成"""
        telemetry().emit(
            "V5PLUS_STAGE2_SKIP",
            session_id=self._session_id,
        )
        logger.info("Stage 2: skipped → direct generate")
        self.skipped.emit(self._text)

    def _on_generate(self):
        """开始生成 → emit strategy_config"""
        config = {
            "strategy": self._selected_strategy,
            "audience": self._audience_input.text().strip(),
            "duration": self._duration_combo.currentData() or "10",
            "doc_type": self._analysis["doc_type"] if self._analysis else "general",
            "text": self._text,
        }

        telemetry().emit(
            "V5PLUS_STAGE2_SUBMIT",
            session_id=self._session_id,
            strategy=self._selected_strategy,
            audience=config["audience"],
            duration=config["duration"],
        )
        logger.info("Stage 2: generate with strategy=%s, audience='%s', duration=%s",
                     self._selected_strategy, config["audience"], config["duration"])

        # AI stub：Pipeline 生成留空
        print(f"[V5Plus] AI stub: Pipeline generate (strategy={self._selected_strategy})")

        self.submitted.emit(config)

    # =========================================================================
    # 样式工具
    # =========================================================================

    @staticmethod
    def _card_style(color: str, selected: bool) -> str:
        border = f"2px solid {color}" if selected else f"1px solid {T.STROKE_SUBTLE}"
        bg = f"rgba({color.lstrip('#')[0:2]}, {color.lstrip('#')[2:4]}, {color.lstrip('#')[4:6]}, 20)" if selected else T.BG_ELEVATED
        # 用 hex alpha 近似
        if selected:
            bg = T.BG_SELECTED
        else:
            bg = T.BG_ELEVATED
        return f"""
            QFrame {{
                background-color: {bg};
                border-radius: 10px;
                border: {border};
            }}
            QFrame:hover {{
                border: 2px solid {color};
            }}
        """

    @staticmethod
    def _input_style():
        return f"""
            QLineEdit {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QLineEdit:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
        """

    @staticmethod
    def _combo_style():
        return f"""
            QComboBox {{
                background-color: {T.BG_INPUT};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QComboBox:focus {{ border: 1px solid {T.STROKE_FOCUS}; }}
            QComboBox::drop-down {{
                border: none; width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {T.BG_ELEVATED};
                color: {T.TEXT_PRIMARY};
                border: 1px solid {T.STROKE_BORDER};
                selection-background-color: {T.BG_SELECTED};
            }}
        """

    @staticmethod
    def _cta_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_PRIMARY_BG};
                color: {T.BTN_PRIMARY_TEXT};
                border: none; border-radius: 8px;
                padding: 8px 24px;
                font-size: {T.FONT_BODY[0] + 1}px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.BTN_PRIMARY_HOVER}; }}
        """

    @staticmethod
    def _secondary_btn_style():
        return f"""
            QPushButton {{
                background-color: {T.BTN_ACTION_BG};
                color: {T.TEXT_SECONDARY};
                border: 1px solid {T.STROKE_SUBTLE};
                border-radius: 8px;
                padding: 6px 16px;
                font-size: {T.FONT_BODY[0]}px;
            }}
            QPushButton:hover {{
                background-color: {T.BTN_ACTION_HOVER};
                color: {T.TEXT_PRIMARY};
            }}
        """
