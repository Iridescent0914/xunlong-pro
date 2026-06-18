"""
-
"""
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import re

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager


class SectionEvaluator:
    """TODO: Add docstring."""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager,
        confidence_threshold: float = 0.7
    ):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.confidence_threshold = confidence_threshold
        self.name = ""

    async def evaluate_section(
        self,
        section_result: Dict[str, Any],
        section_requirements: Dict[str, Any],
        available_sources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """TODO: Add docstring."""

        section_id = section_result.get("section_id")
        logger.info(f"[{self.name}]  {section_id}")

        try:
            # 
            evaluation_prompt = self._build_evaluation_prompt(
                section_result, section_requirements, available_sources
            )

            # LLM
            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                evaluation_prompt,
                ""
            )

            # 
            evaluation = self._parse_evaluation_response(response)

            # 
            confidence = self._calculate_overall_confidence(evaluation)

            # 
            passed = confidence >= self.confidence_threshold

            # 
            recommendation = self._generate_recommendation(
                evaluation, confidence, passed
            )

            result = {
                "section_id": section_id,
                "passed": passed,
                "confidence": confidence,
                "scores": evaluation.get("scores", {}),
                "issues": evaluation.get("issues", []),
                "recommendation": recommendation,
                "status": "success"
            }

            logger.info(
                f"[{self.name}]  {section_id} "
                f": {confidence:.2f}, : {passed}"
            )

            return result

        except Exception as e:
            logger.error(f"[{self.name}]  {section_id} : {e}")
            return {
                "section_id": section_id,
                "passed": False,
                "confidence": 0.0,
                "scores": {},
                "issues": [f": {str(e)}"],
                "recommendation": {
                    "action": "need_rewrite",
                    "reason": "",
                    "suggestions": [""]
                },
                "status": "error",
                "error": str(e)
            }

    def _build_evaluation_prompt(
        self,
        section_result: Dict[str, Any],
        section_requirements: Dict[str, Any],
        available_sources: Optional[List[Dict[str, Any]]]
    ) -> str:
        """构建评估 prompt，从 YAML 加载系统提示词。"""

        section_id = section_result.get("section_id")
        title = section_result.get("title")
        content = section_result.get("content")
        requirements = section_requirements.get("requirements", "")
        target_word_count = section_requirements.get("word_count", 500)

        sources_summary = ""
        if available_sources:
            sources_summary = "\n".join([
                f"- {s.get('title', '')}"
                for s in available_sources[:5]
            ])

        # 构建评估任务描述
        evaluation_task = f"""评估章节是否满足以下要求：
        要求：{requirements}
        目标字数：{target_word_count}
        实际字数：{len(content)}"""

        # 尝试从 YAML 加载 prompt
        try:
            prompt = self.prompt_manager.get_prompt(
                "agents/report/section_evaluator",
                evaluation_task=evaluation_task,
                section_title=title,
                section_content=content
            )
            # 追加参考资料
            if sources_summary:
                prompt += f"\n\n## 参考资料\n{sources_summary}"
        except (KeyError, Exception) as e:
            logger.warning(f"[{self.name}] YAML prompt load failed, using fallback: {e}")
            prompt = f"""# 任务

## 基本信息
- 章节ID: {section_id}
- 标题: {title}
- 目标字数: {target_word_count}
- 实际字数: {len(content)}

## 评估要求
{requirements}

## 待评估内容
{content}

## 参考资料
{sources_summary if sources_summary else "无参考资料"}

## 评估维度

请从以下几个维度对内容进行评分（0-10分制）：

### 1. 完整性 (Completeness)
- 内容是否完整
- 是否遗漏关键信息
- 是否覆盖所有要点

### 2. 准确性 (Accuracy)
- 事实是否准确
- 数据是否可靠
- 论述是否合理

### 3. 相关性 (Relevance)
- 是否紧扣主题
- 是否满足用户需求
- 内容是否切题

### 4. 连贯性 (Coherence)
- 逻辑是否清晰
- 结构是否合理
- 表达是否流畅

## 输出要求

请按照以下 JSON 格式输出评估结果：

```json
{{
  "scores": {{
    "completeness": 8.0,
    "accuracy": 9.0,
    "relevance": 8.5,
    "coherence": 7.5
  }},
  "issues": [
    "问题1",
    "问题2"
  ],
  "strengths": [
    "优点1",
    "优点2"
  ],
  "missing_info": [
    "缺失信息1",
    "缺失信息2"
  ],
  "suggestions": [
    "建议1",
    "建议2"
  ]
}}
```

## 评分标准

- **9-10分**: 优秀，无需修改
- **7-8分**: 良好，有小问题
- **5-6分**: 一般，需要修改
- **3-4分**: 较差，需要较大修改
- **0-2分**: 很差，需要重写

"""

        return prompt

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """TODO: Add docstring."""

        try:
            # JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                evaluation = json.loads(json_str)

                # 
                if "scores" in evaluation:
                    return evaluation

            logger.warning(f"[{self.name}] JSON")
            return self._get_fallback_evaluation()

        except Exception as e:
            logger.error(f"[{self.name}] : {e}")
            return self._get_fallback_evaluation()

    def _get_fallback_evaluation(self) -> Dict[str, Any]:
        """TODO: Add docstring."""
        return {
            "scores": {
                "completeness": 6.0,
                "accuracy": 6.0,
                "relevance": 6.0,
                "coherence": 6.0
            },
            "issues": [""],
            "strengths": [],
            "missing_info": [],
            "suggestions": [""]
        }

    def _calculate_overall_confidence(self, evaluation: Dict[str, Any]) -> float:
        """TODO: Add docstring."""

        scores = evaluation.get("scores", {})

        # 
        weights = {
            "completeness": 0.30,
            "accuracy": 0.30,
            "relevance": 0.25,
            "coherence": 0.15
        }

        # 0-10  0-1
        total_score = 0.0
        total_weight = 0.0

        for criterion, weight in weights.items():
            if criterion in scores:
                score = scores[criterion] / 10.0  #  0-1
                total_score += score * weight
                total_weight += weight

        if total_weight > 0:
            confidence = total_score / total_weight
        else:
            confidence = 0.5

        return round(confidence, 2)

    def _generate_recommendation(
        self,
        evaluation: Dict[str, Any],
        confidence: float,
        passed: bool
    ) -> Dict[str, Any]:
        """TODO: Add docstring."""

        if passed:
            return {
                "action": "approve",
                "reason": f" {confidence:.2f} ",
                "suggestions": []
            }

        scores = evaluation.get("scores", {})
        issues = evaluation.get("issues", [])
        missing_info = evaluation.get("missing_info", [])
        suggestions = evaluation.get("suggestions", [])

        # 
        avg_score = sum(scores.values()) / len(scores) if scores else 5.0

        # 
        if missing_info and scores.get("completeness", 10) < 7:
            return {
                "action": "need_more_content",
                "reason": "",
                "missing_info": missing_info,
                "suggestions": suggestions
            }

        # 
        if avg_score < 6:
            return {
                "action": "need_rewrite",
                "reason": "",
                "issues": issues,
                "suggestions": suggestions
            }

        # 
        return {
            "action": "need_rewrite",
            "reason": f" {confidence:.2f}  {self.confidence_threshold}",
            "issues": issues,
            "suggestions": suggestions
        }

    async def batch_evaluate(
        self,
        section_results: List[Dict[str, Any]],
        section_requirements: List[Dict[str, Any]],
        available_sources: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """TODO: Add docstring."""

        logger.info(f"[{self.name}]  {len(section_results)} ")

        # 
        tasks = []
        for section_result in section_results:
            section_id = section_result.get("section_id")
            # 
            requirements = next(
                (r for r in section_requirements if r.get("id") == section_id),
                {}
            )
            task = self.evaluate_section(section_result, requirements, available_sources)
            tasks.append(task)

        # 
        evaluations = await asyncio.gather(*tasks, return_exceptions=True)

        # 
        results = []
        for i, evaluation in enumerate(evaluations):
            if isinstance(evaluation, Exception):
                logger.error(f"[{self.name}]  {i+1} : {evaluation}")
                results.append({
                    "section_id": i + 1,
                    "passed": False,
                    "confidence": 0.0,
                    "status": "error",
                    "error": str(evaluation)
                })
            else:
                results.append(evaluation)

        passed_count = sum(1 for r in results if r.get("passed"))
        logger.info(f"[{self.name}] {passed_count}/{len(results)} ")

        return results
