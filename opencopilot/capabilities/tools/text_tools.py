"""
文本处理工具
"""

import asyncio
import re
from typing import Any, Dict, List
from .base import BaseTool


class TextExtractTool(BaseTool):
    """文本提取工具"""
    
    @property
    def name(self) -> str:
        return "text_extract"
    
    @property
    def description(self) -> str:
        return "从各种格式中提取文本"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "content": {
                "type": "string",
                "description": "要提取的内容",
                "required": True
            },
            "extract_type": {
                "type": "string",
                "description": "提取类型",
                "enum": ["all", "headings", "key_points", "summary", "tables", "lists"],
                "default": "all"
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文本提取"""
        content = kwargs.get("content")
        extract_type = kwargs.get("extract_type", "all")
        
        if not content:
            return {"error": "content is required"}
        
        try:
            if extract_type == "headings":
                return self._extract_headings(content)
            elif extract_type == "key_points":
                return self._extract_key_points(content)
            elif extract_type == "summary":
                return self._generate_summary(content)
            elif extract_type == "tables":
                return self._extract_tables(content)
            elif extract_type == "lists":
                return self._extract_lists(content)
            else:
                return {"type": "all", "content": content}
        except Exception as e:
            return {"error": f"文本提取失败: {str(e)}"}
    
    def _extract_headings(self, content: str) -> Dict[str, Any]:
        """提取标题"""
        # 匹配Markdown标题
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        headings = []
        
        for line in content.split('\n'):
            match = re.match(heading_pattern, line, re.MULTILINE)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append({"level": level, "text": text})
        
        return {
            "type": "headings",
            "headings": headings,
            "count": len(headings)
        }
    
    def _extract_key_points(self, content: str) -> Dict[str, Any]:
        """提取关键点"""
        # 简单的关键点提取逻辑
        sentences = re.split(r'[。！？.!?]', content)
        key_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 200:
                # 过滤掉太短或太长的句子
                key_points.append(sentence)
        
        # 限制关键点数量
        key_points = key_points[:10]
        
        return {
            "type": "key_points",
            "key_points": key_points,
            "count": len(key_points)
        }
    
    def _generate_summary(self, content: str) -> Dict[str, Any]:
        """生成摘要"""
        # 简单的摘要生成逻辑
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        # 取前3个句子作为摘要
        summary_sentences = sentences[:3]
        summary = '。'.join(summary_sentences) + '。' if summary_sentences else ""
        
        return {
            "type": "summary",
            "summary": summary,
            "original_length": len(content),
            "summary_length": len(summary)
        }
    
    def _extract_tables(self, content: str) -> Dict[str, Any]:
        """提取表格"""
        # 匹配Markdown表格
        table_pattern = r'\|(.+)\|\n\|[-\s|]+\|\n((?:\|.+\|\n)*)'
        tables = []
        
        for match in re.finditer(table_pattern, content, re.MULTILINE):
            header = match.group(1).strip()
            rows = match.group(2).strip().split('\n')
            
            table_data = {
                "header": [cell.strip() for cell in header.split('|') if cell.strip()],
                "rows": []
            }
            
            for row in rows:
                if row.strip():
                    cells = [cell.strip() for cell in row.split('|') if cell.strip()]
                    table_data["rows"].append(cells)
            
            tables.append(table_data)
        
        return {
            "type": "tables",
            "tables": tables,
            "count": len(tables)
        }
    
    def _extract_lists(self, content: str) -> Dict[str, Any]:
        """提取列表"""
        # 匹配无序列表
        unordered_pattern = r'^[\s]*[-*+]\s+(.+)$'
        # 匹配有序列表
        ordered_pattern = r'^[\s]*\d+\.\s+(.+)$'
        
        unordered_items = []
        ordered_items = []
        
        for line in content.split('\n'):
            unordered_match = re.match(unordered_pattern, line, re.MULTILINE)
            ordered_match = re.match(ordered_pattern, line, re.MULTILINE)
            
            if unordered_match:
                unordered_items.append(unordered_match.group(1).strip())
            elif ordered_match:
                ordered_items.append(ordered_match.group(1).strip())
        
        return {
            "type": "lists",
            "unordered_items": unordered_items,
            "ordered_items": ordered_items,
            "unordered_count": len(unordered_items),
            "ordered_count": len(ordered_items)
        }


class TextTransformTool(BaseTool):
    """文本转换工具"""
    
    @property
    def name(self) -> str:
        return "text_transform"
    
    @property
    def description(self) -> str:
        return "转换文本格式和风格"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "text": {
                "type": "string",
                "description": "要转换的文本",
                "required": True
            },
            "transform_type": {
                "type": "string",
                "description": "转换类型",
                "enum": ["formal", "casual", "concise", "detailed", "academic", "business"],
                "required": True
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文本转换"""
        text = kwargs.get("text")
        transform_type = kwargs.get("transform_type")
        
        if not text or not transform_type:
            return {"error": "text and transform_type are required"}
        
        try:
            if transform_type == "formal":
                return await self._make_formal(text)
            elif transform_type == "casual":
                return await self._make_casual(text)
            elif transform_type == "concise":
                return await self._make_concise(text)
            elif transform_type == "detailed":
                return await self._make_detailed(text)
            elif transform_type == "academic":
                return await self._make_academic(text)
            elif transform_type == "business":
                return await self._make_business(text)
            else:
                return {"error": f"不支持的转换类型: {transform_type}"}
        except Exception as e:
            return {"error": f"文本转换失败: {str(e)}"}
    
    async def _make_formal(self, text: str) -> Dict[str, Any]:
        """转换为正式风格"""
        # 简单的正式化处理
        formal_text = text
        
        # 替换口语化表达
        replacements = {
            "我觉得": "我认为",
            "挺好的": "相当不错",
            "超级": "非常",
            "巨": "非常",
            "贼": "非常",
            "咋": "怎么",
            "啥": "什么",
            "咋样": "怎么样",
        }
        
        for informal, formal in replacements.items():
            formal_text = formal_text.replace(informal, formal)
        
        return {
            "type": "formal",
            "original": text,
            "transformed": formal_text,
            "changes": len(replacements)
        }
    
    async def _make_casual(self, text: str) -> Dict[str, Any]:
        """转换为随意风格"""
        casual_text = text
        
        # 替换正式表达
        replacements = {
            "我认为": "我觉得",
            "相当不错": "挺好的",
            "非常": "超级",
            "怎么": "咋",
            "什么": "啥",
            "怎么样": "咋样",
        }
        
        for formal, casual in replacements.items():
            casual_text = casual_text.replace(formal, casual)
        
        return {
            "type": "casual",
            "original": text,
            "transformed": casual_text,
            "changes": len(replacements)
        }
    
    async def _make_concise(self, text: str) -> Dict[str, Any]:
        """转换为简洁风格"""
        # 移除冗余词汇
        concise_text = text
        
        # 移除冗余词汇
        redundant_words = ["非常", "很", "十分", "极其", "特别", "相当"]
        for word in redundant_words:
            concise_text = concise_text.replace(f"{word}的", "")
            concise_text = concise_text.replace(f"{word}地", "")
        
        # 移除重复的标点
        concise_text = re.sub(r'[。！？.!?]{2,}', '。', concise_text)
        
        return {
            "type": "concise",
            "original": text,
            "transformed": concise_text,
            "original_length": len(text),
            "concise_length": len(concise_text)
        }
    
    async def _make_detailed(self, text: str) -> Dict[str, Any]:
        """转换为详细风格"""
        # 添加细节描述
        detailed_text = text
        
        # 在适当位置添加细节
        if "。" in detailed_text:
            sentences = detailed_text.split("。")
            detailed_sentences = []
            for sentence in sentences:
                if sentence.strip():
                    # 简单的细节添加逻辑
                    if len(sentence) < 20:
                        detailed_sentences.append(f"{sentence}，这是一个重要的方面。")
                    else:
                        detailed_sentences.append(sentence)
            detailed_text = "。".join(detailed_sentences)
        
        return {
            "type": "detailed",
            "original": text,
            "transformed": detailed_text,
            "original_length": len(text),
            "detailed_length": len(detailed_text)
        }
    
    async def _make_academic(self, text: str) -> Dict[str, Any]:
        """转换为学术风格"""
        academic_text = text
        
        # 替换非学术表达
        replacements = {
            "我觉得": "本研究认为",
            "大家都知道": "众所周知",
            "很多人": "众多学者",
            "可能": "或许",
            "一定": "必然",
        }
        
        for informal, academic in replacements.items():
            academic_text = academic_text.replace(informal, academic)
        
        return {
            "type": "academic",
            "original": text,
            "transformed": academic_text,
            "changes": len(replacements)
        }
    
    async def _make_business(self, text: str) -> Dict[str, Any]:
        """转换为商务风格"""
        business_text = text
        
        # 替换非商务表达
        replacements = {
            "你好": "尊敬的领导/同事",
            "谢谢": "感谢",
            "对不起": "抱歉",
            "尽快": "及时",
            "马上": "立即",
        }
        
        for informal, business in replacements.items():
            business_text = business_text.replace(informal, business)
        
        return {
            "type": "business",
            "original": text,
            "transformed": business_text,
            "changes": len(replacements)
        }