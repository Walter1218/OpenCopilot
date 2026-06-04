"""
原文匹配器

负责追踪幻灯片内容与原文的对应关系：
- 匹配幻灯片标题和 items 到原文位置
- 计算已提炼范围
- 支持双向联动
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


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


class SourceMatcher:
    """原文匹配器"""
    
    def __init__(self):
        self.mappings: List[SourceMapping] = []
        self.extracted_ranges: List[TextRange] = []
        self.selected_ranges: List[TextRange] = []
    
    def build_mappings(self, original_text: str, slides: List[dict]) -> None:
        """构建幻灯片内容与原文的映射关系"""
        self.mappings.clear()
        self.extracted_ranges.clear()
        
        for slide_idx, slide in enumerate(slides):
            # 匹配标题
            title = slide.get('title', '')
            if title:
                ranges = self._find_text_in_source(original_text, title)
                for r in ranges:
                    self.mappings.append(SourceMapping(
                        slide_index=slide_idx,
                        item_index=None,
                        source_range=r
                    ))
                    self.extracted_ranges.append(r)
            
            # 匹配副标题
            subtitle = slide.get('subtitle', '')
            if subtitle:
                ranges = self._find_text_in_source(original_text, subtitle)
                for r in ranges:
                    self.mappings.append(SourceMapping(
                        slide_index=slide_idx,
                        item_index=-1,  # -1 表示副标题
                        source_range=r
                    ))
                    self.extracted_ranges.append(r)
            
            # 匹配每个 item
            for item_idx, item in enumerate(slide.get('items', [])):
                item_text = item.get('text', '')
                if item_text:
                    ranges = self._find_text_in_source(original_text, item_text)
                    for r in ranges:
                        self.mappings.append(SourceMapping(
                            slide_index=slide_idx,
                            item_index=item_idx,
                            source_range=r
                        ))
                        self.extracted_ranges.append(r)
        
        # 合并重叠的已提炼范围
        self.extracted_ranges = self._merge_ranges(self.extracted_ranges)
    
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
