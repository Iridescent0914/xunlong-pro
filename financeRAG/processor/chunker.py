"""文本切块模块 - 使用滑动窗口"""

from typing import List, Tuple
from loguru import logger


class TextChunker:
    """文本切块器 - 使用滑动窗口"""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 100):
        """
        初始化切块器
        
        Args:
            chunk_size: 每个切块的字符数
            overlap: 相邻切块的重叠字符数
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        if overlap >= chunk_size:
            logger.warning(f"重叠({overlap})大于等于块大小({chunk_size})，自动调整为块大小的1/3")
            self.overlap = max(1, chunk_size // 3)
    
    def chunk_text(self, text: str, chunk_id_prefix: str = "") -> List[dict]:
        """
        使用滑动窗口将文本分块
        
        Args:
            text: 要分块的文本
            chunk_id_prefix: 块ID前缀
            
        Returns:
            切块列表，每个元素包含内容和元数据
        """
        if not text:
            return []
        
        text = text.strip()
        chunks = []
        
        # 如果文本小于块大小，直接返回整个文本
        if len(text) <= self.chunk_size:
            return [{
                'content': text,
                'chunk_index': 0,
                'start_char': 0,
                'end_char': len(text),
                'chunk_size': self.chunk_size,
                'overlap': self.overlap,
            }]
        
        # 使用滑动窗口进行切块
        step = self.chunk_size - self.overlap
        idx = 0
        
        for start in range(0, len(text), step):
            end = min(start + self.chunk_size, len(text))
            
            chunk_content = text[start:end]
            
            # 避免最后一个块太短
            if len(text) - end < self.chunk_size * 0.1 and end < len(text):
                # 合并到上一个块
                if chunks:
                    chunks[-1]['content'] += chunk_content[chunks[-1]['overlap']:]
                    chunks[-1]['end_char'] = end
                break
            
            chunks.append({
                'content': chunk_content,
                'chunk_index': idx,
                'start_char': start,
                'end_char': end,
                'chunk_size': self.chunk_size,
                'overlap': self.overlap,
            })
            
            idx += 1
            
            # 如果已到达文本末尾，停止
            if end >= len(text):
                break
        
        return chunks
    
    def chunk_by_sentences(
        self, 
        text: str, 
        max_chars: int = 1000,
        sentence_endings: str = '。！？.\n'
    ) -> List[dict]:
        """
        按句子进行分块（更尊重句子边界）
        
        Args:
            text: 要分块的文本
            max_chars: 单个块最大字符数
            sentence_endings: 句子结尾符号
            
        Returns:
            切块列表
        """
        if not text:
            return []
        
        text = text.strip()
        chunks = []
        current_chunk = ""
        start_pos = 0
        chunk_idx = 0
        
        # 分离句子
        sentences = []
        current_sentence = ""
        
        for i, char in enumerate(text):
            current_sentence += char
            if char in sentence_endings:
                sentences.append((current_sentence, start_pos))
                start_pos = i + 1
                current_sentence = ""
        
        if current_sentence:
            sentences.append((current_sentence, start_pos))
        
        # 按句子组合成块
        for sentence, sent_start_pos in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk,
                        'chunk_index': chunk_idx,
                        'start_char': sent_start_pos - len(current_chunk),
                        'end_char': sent_start_pos,
                        'chunk_size': max_chars,
                        'overlap': 0,
                    })
                    chunk_idx += 1
                current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk:
            chunks.append({
                'content': current_chunk,
                'chunk_index': chunk_idx,
                'start_char': len(text) - len(current_chunk),
                'end_char': len(text),
                'chunk_size': max_chars,
                'overlap': 0,
            })
        
        return chunks
    
    @staticmethod
    def estimate_chunks_count(text: str, chunk_size: int = 512, overlap: int = 100) -> int:
        """
        估计文本会被分成多少个块
        
        Args:
            text: 文本
            chunk_size: 块大小
            overlap: 重叠大小
            
        Returns:
            估计的块数
        """
        if not text or len(text) <= chunk_size:
            return 1
        
        step = chunk_size - overlap
        return (len(text) - chunk_size) // step + 1
