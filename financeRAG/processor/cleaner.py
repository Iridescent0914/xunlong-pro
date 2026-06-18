"""文本清洗模块"""

import re
from typing import List, Tuple
from loguru import logger


class TextCleaner:
    """文本清洗器"""
    
    def __init__(self):
        """初始化清洗规则"""
        self.rules: List[Tuple[str, str]] = [
            # 移除 HTML 标签
            (r'<[^>]+>', ''),
            # 移除 HTML 实体
            (r'&nbsp;', ' '),
            (r'&lt;', '<'),
            (r'&gt;', '>'),
            (r'&amp;', '&'),
            # 移除 URL
            (r'https?://[^\s]+', ''),
            # 移除邮箱
            (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', ''),
            # 移除多个空格
            (r' +', ' '),
            # 移除多个换行
            (r'\n{3,}', '\n\n'),
            # 移除制表符
            (r'\t+', ' '),
            # 移除特殊符号（保留常用标点）
            (r'[\u200B-\u200D\uFEFF]', ''),  # 零宽字符
        ]
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 应用所有清洗规则
        for pattern, replacement in self.rules:
            text = re.sub(pattern, replacement, text)
        
        # 删除开头和结尾的空白
        text = text.strip()
        
        return text
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        批量清洗文本
        
        Args:
            texts: 文本列表
            
        Returns:
            清洗后的文本列表
        """
        return [self.clean(text) for text in texts]
    
    @staticmethod
    def is_valid_text(text: str, min_length: int = 10) -> bool:
        """
        检查文本是否有效
        
        Args:
            text: 文本内容
            min_length: 最小长度阈值
            
        Returns:
            是否有效
        """
        if not text:
            return False
        
        # 检查长度
        if len(text.strip()) < min_length:
            return False
        
        # 检查是否全是特殊字符或空白
        if not re.search(r'[a-zA-Z0-9\u4e00-\u9fff]', text):
            return False
        
        return True
    
    @staticmethod
    def get_text_stats(text: str) -> dict:
        """
        获取文本统计信息
        
        Args:
            text: 文本内容
            
        Returns:
            统计信息字典
        """
        return {
            'total_chars': len(text),
            'total_lines': len(text.split('\n')),
            'total_words': len(text.split()),
            'has_chinese': bool(re.search(r'[\u4e00-\u9fff]', text)),
            'has_english': bool(re.search(r'[a-zA-Z]', text)),
            'has_numbers': bool(re.search(r'\d', text)),
        }
