"""内容评估智能体 - 评估搜索结果与用户查询的相关性。"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import json
from loguru import logger

from ..llm.manager import LLMManager
from ..llm.prompts import PromptManager
from ..tools.time_tool import time_tool


class ContentEvaluator:
    """内容评估智能体，负责评估搜索结果与用户查询的相关性。"""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = "内容评估智能体"

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """评估内容与查询的相关性。"""
        content_items = data.get("content_items", [])
        query = data.get("query", "")
        time_context = data.get("time_context", {})

        result = await self.evaluate_content(content_items, query, time_context)
        return {
            "agent": self.name,
            "result": result,
            "status": "success" if result.get("relevant_content") else "failed"
        }

    async def evaluate_content_relevance(
        self,
        query: str,
        content_items: List[Dict[str, Any]],
        time_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """评估内容与查询的相关性，返回相关的内容列表。"""
        logger.info(f"[{self.name}] 评估 {len(content_items)} 条内容")

        if not time_context:
            time_context = time_tool.parse_date_query(query)

        evaluation_tasks = []
        for i, item in enumerate(content_items):
            task = self._evaluate_single_item(query, item, time_context, i)
            evaluation_tasks.append(task)

        evaluations = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        relevant_items = []
        for i, evaluation in enumerate(evaluations):
            if isinstance(evaluation, Exception):
                logger.error(f"[{self.name}] 第 {i} 条评估异常: {evaluation}")
                continue

            if evaluation and evaluation.get("is_relevant", False):
                item = content_items[i].copy()
                item["evaluation"] = evaluation
                relevant_items.append(item)
                logger.info(f"[{self.name}] 第 {i} 条相关: {evaluation.get('relevance_score', 0)}")
            else:
                logger.debug(f"[{self.name}] 第 {i} 条不相关")

        logger.info(f"[{self.name}] 筛选结果: {len(relevant_items)}/{len(content_items)} 条相关")
        return relevant_items

    async def _evaluate_single_item(
        self,
        query: str,
        item: Dict[str, Any],
        time_context: Dict[str, Any],
        index: int
    ) -> Optional[Dict[str, Any]]:
        """评估单条内容。"""
        try:
            evaluation_prompt = self._build_evaluation_prompt(query, item, time_context)

            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                evaluation_prompt,
                ""
            )

            evaluation = self._parse_evaluation_response(response)
            return evaluation

        except Exception as e:
            logger.error(f"[{self.name}] 第 {index} 条评估失败: {e}")
            return None

    def _build_evaluation_prompt(
        self,
        query: str,
        item: Dict[str, Any],
        time_context: Dict[str, Any]
    ) -> str:
        """构建评估 prompt，从 YAML 加载系统提示词。"""
        system_prompt = self.prompt_manager.get_prompt(
            "agents/content_evaluator/system",
            default="你是一个专业的内容相关性评估专家，负责评估搜索获取的内容是否与用户查询相关。"
        )

        title = item.get("title", "")
        content = item.get("content", "")[:1500]
        url = item.get("url", "")

        extracted_dates = time_context.get("extracted_dates", [])
        current_time = time_context.get("current_time", {})

        return f"""{system_prompt}

## 评估任务
请评估以下内容与用户查询的相关性。

## 用户查询
{query}

## 时间信息
- 当前时间: {current_time.get('current_datetime', '')}
- 查询指定日期: {[d['formatted'] for d in extracted_dates] if extracted_dates else '无特定日期要求'}

## 待评估内容
- 标题: {title}
- URL: {url}
- 内容: {content}

## 评估要求
请从以下三个维度评估（每个维度 0-10 分）：
1. **主题相关性 (topic_score)**: 内容与查询主题的匹配程度
2. **时间相关性 (time_score)**: 内容时间与查询要求的匹配程度
3. **内容质量 (quality_score)**: 内容的详细程度和可信度

## 输出要求
请严格按照以下 JSON 格式输出评估结果：
```json
{{
  "is_relevant": true或false（总分>=15为true，否则为false）,
  "relevance_score": 总分（0-30，三个维度之和）,
  "topic_score": 主题相关性分数（0-10）,
  "time_score": 时间相关性分数（0-10）,
  "quality_score": 内容质量分数（0-10）,
  "reason": "评分理由（简要说明）",
  "extracted_time": "从内容中提取的时间（如有）"
}}
```

请直接输出 JSON 结果："""

    def _parse_evaluation_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析评估响应。"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                evaluation = json.loads(json_str)

                required_fields = ["is_relevant", "relevance_score", "topic_score", "time_score", "quality_score"]
                if all(field in evaluation for field in required_fields):
                    return evaluation

            logger.warning(f"[{self.name}] JSON 解析失败，使用默认评估")
            return self._fallback_parse(response)

        except Exception as e:
            logger.error(f"[{self.name}] 解析评估响应失败: {e}")
            return None

    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """解析失败时的默认处理。"""
        is_relevant = "相关" in response or "匹配" in response or "true" in response.lower()

        score_match = re.search(r'(\d+)', response)
        score = int(score_match.group(1)) if score_match else (20 if is_relevant else 5)

        return {
            "is_relevant": is_relevant,
            "relevance_score": score,
            "topic_score": min(score, 10),
            "time_score": min(score // 2, 10),
            "quality_score": min(score // 2, 10),
            "reason": "默认评估",
            "extracted_time": ""
        }

    async def filter_by_time_relevance(
        self,
        content_items: List[Dict[str, Any]],
        target_dates: List[str],
        tolerance_days: int = 2
    ) -> List[Dict[str, Any]]:
        """按时间相关性过滤内容。"""
        if not target_dates:
            return content_items

        filtered_items = []

        for item in content_items:
            extracted_time = self._extract_time_from_content(item)

            if extracted_time:
                is_time_relevant = any(
                    time_tool.is_date_relevant(extracted_time, target_date, tolerance_days)
                    for target_date in target_dates
                )

                if is_time_relevant:
                    item["extracted_time"] = extracted_time
                    filtered_items.append(item)
                else:
                    logger.debug(f"[{self.name}] 时间不匹配: {extracted_time} vs {target_dates}")
            else:
                item["extracted_time"] = ""
                filtered_items.append(item)

        return filtered_items

    def _extract_time_from_content(self, item: Dict[str, Any]) -> Optional[str]:
        """从内容中提取时间信息。"""
        text = f"{item.get('title', '')} {item.get('content', '')}"

        patterns = [
            r'(\d{4})(\d{1,2})(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{1,2})(\d{1,2})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                match = matches[0]
                if len(match) == 3:
                    year, month, day = match
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(match) == 2:
                    month, day = match
                    current_year = datetime.now().year
                    return f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"

        return None
