"""
原文匹配器

负责追踪幻灯片内容与原文的对应关系：
- 匹配幻灯片标题和 items 到原文位置
- 优先使用 LLM 提供的 source_excerpt 进行高质量映射
- 计算已提炼范围
- 支持双向联动
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TextRange:
    """文本范围"""
    start: int
    end: int
    text: str = ""
    
    def contains(self, pos: int) -> bool:
        return self.start <= pos < self.end
    
    def overlaps(self, other: 'TextRange') -> bool:
        return self.start < other.end and other.start < self.end
    
    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class SourceMapping:
    """原文映射关系"""
    slide_index: int
    item_index: Optional[int]  # None 表示标题
    source_range: TextRange
    mapping_source: str = "fallback"  # "llm" = source_excerpt 命中, "fallback" = 文本匹配


class SourceMatcher:
    """原文匹配器"""
    
    def __init__(self):
        self.mappings: List[SourceMapping] = []
        self.extracted_ranges: List[TextRange] = []
        self.selected_ranges: List[TextRange] = []
    
    def build_mappings(self, original_text: str, slides: List[dict]) -> None:
        """构建幻灯片内容与原文的映射关系
        
        优先使用 LLM 提供的 source_excerpt 进行高质量映射，
        回退到文本子串匹配。
        """
        self.mappings.clear()
        self.extracted_ranges.clear()
        
        # 统计指标
        llm_hits = 0
        fallback_hits = 0
        total_slides = len(slides)
        
        for slide_idx, slide in enumerate(slides):
            if not isinstance(slide, dict):
                logger.warning("[SourceMatcher] skip invalid slide at index %s: %s", slide_idx, type(slide).__name__)
                continue
            # ---- 优先尝试 source_excerpt（LLM 标记的原文片段）----
            source_excerpt = slide.get('source_excerpt', '')
            excerpt_range = None
            if source_excerpt:
                excerpt_range = self._find_excerpt_in_source(original_text, source_excerpt)
                if excerpt_range:
                    llm_hits += 1
                    # 用 source_excerpt 的范围建立整页级映射
                    self.mappings.append(SourceMapping(
                        slide_index=slide_idx,
                        item_index=None,
                        source_range=excerpt_range,
                        mapping_source="llm"
                    ))
                    self.extracted_ranges.append(excerpt_range)
                    logger.debug(f"[SourceMatcher] Slide {slide_idx}: source_excerpt 命中 "
                                 f"(pos={excerpt_range.start}-{excerpt_range.end})")
            
            # ---- 标题匹配 ----
            title = slide.get('title', '')
            if title:
                ranges = self._find_text_in_source(original_text, title)
                if ranges:
                    fallback_hits += (1 if not excerpt_range else 0)
                    for r in ranges:
                        self.mappings.append(SourceMapping(
                            slide_index=slide_idx,
                            item_index=None,
                            source_range=r,
                            mapping_source="fallback" if not excerpt_range else "llm_title"
                        ))
                        self.extracted_ranges.append(r)
            
            # ---- 副标题匹配 ----
            subtitle = slide.get('subtitle', '')
            if subtitle:
                ranges = self._find_text_in_source(original_text, subtitle)
                for r in ranges:
                    self.mappings.append(SourceMapping(
                        slide_index=slide_idx,
                        item_index=-1,  # -1 表示副标题
                        source_range=r,
                        mapping_source="fallback"
                    ))
                    self.extracted_ranges.append(r)
            
            # ---- 每个 item 匹配 ----
            items = slide.get('items', [])
            if not isinstance(items, list):
                logger.warning("[SourceMatcher] slide %s has invalid items type: %s", slide_idx, type(items).__name__)
                continue
            for item_idx, item in enumerate(items):
                if not isinstance(item, dict):
                    logger.warning(
                        "[SourceMatcher] skip invalid item at slide %s item %s: %s",
                        slide_idx,
                        item_idx,
                        type(item).__name__,
                    )
                    continue
                item_text = item.get('text', '')
                if item_text:
                    ranges = self._find_text_in_source(original_text, item_text)
                    if ranges:
                        fallback_hits += 1
                    for r in ranges:
                        self.mappings.append(SourceMapping(
                            slide_index=slide_idx,
                            item_index=item_idx,
                            source_range=r,
                            mapping_source="fallback"
                        ))
                        self.extracted_ranges.append(r)
        
        # 合并重叠的已提炼范围
        self.extracted_ranges = self._merge_ranges(self.extracted_ranges)
        
        # 埋点：记录映射命中率
        total_mappings = len(self.mappings)
        print(f"[SourceMatcher] 映射完成: {total_mappings} 条映射 | "
              f"LLM 命中 {llm_hits}/{total_slides} 页 ({llm_hits*100//max(total_slides,1)}%) | "
              f"回退命中 {fallback_hits} 条 | "
              f"已提炼范围 {len(self.extracted_ranges)} 段")
        logger.info(f"[SourceMatcher] 映射完成: total={total_mappings}, "
                    f"llm_hits={llm_hits}/{total_slides}, fallback={fallback_hits}, "
                    f"extracted_ranges={len(self.extracted_ranges)}")
    
    def _find_excerpt_in_source(self, source: str, excerpt: str) -> Optional[TextRange]:
        """在原文中查找 LLM 提供的 source_excerpt 片段
        
        LLM 摘录的片段可能不是原文的精确子串（可能略有改写），
        所以采用渐进策略：精确匹配 → 去空格匹配 → 关键词锚定
        """
        if not excerpt or not source:
            return None
        
        clean_excerpt = excerpt.strip()
        if len(clean_excerpt) < 5:
            return None
        
        # 策略 1: 精确子串匹配
        pos = source.find(clean_excerpt)
        if pos != -1:
            return TextRange(start=pos, end=pos + len(clean_excerpt), text=clean_excerpt)
        
        # 策略 2: 忽略多余空格的匹配
        # 将 excerpt 中的连续空白替换为单空格，在原文中逐段搜索
        normalized_excerpt = re.sub(r'\s+', ' ', clean_excerpt)
        normalized_source = re.sub(r'\s+', ' ', source)
        pos = normalized_source.find(normalized_excerpt)
        if pos != -1:
            # 映射回原始 source 的位置（粗略）
            # 通过计算 normalized_source[:pos] 中非空白字符数来定位
            real_start = self._map_normalized_to_original(source, pos)
            real_end = self._map_normalized_to_original(source, pos + len(normalized_excerpt))
            return TextRange(start=real_start, end=real_end, 
                             text=source[real_start:real_end])
        
        # 策略 3: 提取 excerpt 的前 15 字和后 15 字作为锚点，在原文中定位
        head = clean_excerpt[:min(15, len(clean_excerpt) // 2)]
        tail = clean_excerpt[-min(15, len(clean_excerpt) // 2):]
        head_pos = source.find(head)
        if head_pos != -1:
            tail_pos = source.find(tail, head_pos + len(head))
            if tail_pos != -1:
                end_pos = tail_pos + len(tail)
                # 扩展到自然边界
                return TextRange(start=head_pos, end=end_pos,
                                 text=source[head_pos:end_pos])
        
        return None
    
    @staticmethod
    def _map_normalized_to_original(source: str, normalized_pos: int) -> int:
        """将 normalized（压缩空格后）的位置映射回原始字符串的位置"""
        count = 0
        for i, ch in enumerate(source):
            if count >= normalized_pos:
                return i
            if not ch.isspace() or (i > 0 and source[i-1] != ' ' and not source[i-1].isspace()):
                count += 1 if not ch.isspace() else 0
                if ch.isspace():
                    count += 1
        return len(source)
    
    def _find_text_in_source(self, source: str, target: str) -> List[TextRange]:
        """在原文中查找目标文本的位置"""
        if not target or not source:
            return []
        
        # 清理 Markdown 标记后再匹配
        clean_target = re.sub(r'\*\*(.*?)\*\*', r'\1', target)
        clean_target = re.sub(r'\*(.*?)\*', r'\1', clean_target)
        clean_target = clean_target.strip()
        
        if not clean_target:
            return []
        
        ranges = []
        # 尝试精确匹配
        start = 0
        while True:
            pos = source.find(clean_target, start)
            if pos == -1:
                break
            ranges.append(TextRange(start=pos, end=pos + len(clean_target), text=clean_target))
            start = pos + 1
        
        # 如果精确匹配失败，尝试模糊匹配（忽略空白字符）
        if not ranges:
            # 将目标文本按空白分割，查找连续匹配
            words = clean_target.split()
            if len(words) >= 2:
                # 使用第一个和最后一个词进行模糊定位
                first_word = words[0]
                last_word = words[-1]
                first_pos = source.find(first_word)
                if first_pos != -1:
                    last_pos = source.find(last_word, first_pos)
                    if last_pos != -1:
                        end_pos = last_pos + len(last_word)
                        # 扩展到完整句子
                        while end_pos < len(source) and source[end_pos] not in '\n。！？.!?':
                            end_pos += 1
                        ranges.append(TextRange(
                            start=first_pos,
                            end=end_pos,
                            text=source[first_pos:end_pos]
                        ))
        
        return ranges
    
    def _merge_ranges(self, ranges: List[TextRange]) -> List[TextRange]:
        """合并重叠的范围"""
        if not ranges:
            return []
        
        sorted_ranges = sorted(ranges, key=lambda r: r.start)
        merged = [sorted_ranges[0]]
        
        for current in sorted_ranges[1:]:
            last = merged[-1]
            if current.start <= last.end:
                # 重叠，合并
                last.end = max(last.end, current.end)
            else:
                merged.append(current)
        
        return merged
    
    def get_extracted_ranges(self) -> List[TextRange]:
        """获取所有已提炼的范围"""
        return self.extracted_ranges
    
    def get_selected_ranges(self) -> List[TextRange]:
        """获取所有用户选中的范围"""
        return self.selected_ranges
    
    def add_selected_range(self, range: TextRange) -> None:
        """添加用户选中的范围"""
        self.selected_ranges.append(range)
    
    def remove_selected_range(self, range: TextRange) -> None:
        """移除用户选中的范围"""
        self.selected_ranges = [r for r in self.selected_ranges if not r.overlaps(range)]
    
    def clear_selected_ranges(self) -> None:
        """清空用户选中的范围"""
        self.selected_ranges.clear()
    
    def find_slide_for_position(self, pos: int) -> Optional[Tuple[int, Optional[int]]]:
        """根据原文位置找到对应的幻灯片和 item"""
        for mapping in self.mappings:
            if mapping.source_range.contains(pos):
                return (mapping.slide_index, mapping.item_index)
        return None
    
    def find_source_position_for_item(self, slide_index: int, item_index: Optional[int]) -> Optional[TextRange]:
        """根据幻灯片和 item 找到对应的原文位置"""
        for mapping in self.mappings:
            if mapping.slide_index == slide_index and mapping.item_index == item_index:
                return mapping.source_range
        return None
    
    def get_text_for_range(self, source: str, range: TextRange) -> str:
        """获取指定范围的原文文本"""
        if 0 <= range.start < range.end <= len(source):
            return source[range.start:range.end]
        return ""
    
    def is_position_extracted(self, pos: int) -> bool:
        """检查某个位置是否已被提炼"""
        return any(r.contains(pos) for r in self.extracted_ranges)
    
    def is_position_selected(self, pos: int) -> bool:
        """检查某个位置是否被用户选中"""
        return any(r.contains(pos) for r in self.selected_ranges)
