"""
 - //PPT
"""
import re
from typing import Dict, Any, Optional
from loguru import logger

from ..llm.manager import LLMManager
from ..llm.prompts import PromptManager


class OutputTypeDetector:
    """TODO: Add docstring."""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = ""

    async def detect_output_type(self, query: str) -> Dict[str, Any]:
        """TODO: Add docstring."""

        logger.info(f"[{self.name}] ")

        # 
        rule_based = self._rule_based_detection(query)
        if rule_based["confidence"] > 0.8:
            logger.info(
                f"[{self.name}] : {rule_based['output_type']} "
                f"(: {rule_based['confidence']:.2f})"
            )
            return rule_based

        # LLM
        logger.info(f"[{self.name}] LLM")
        llm_result = await self._llm_based_detection(query)

        return llm_result

    def _rule_based_detection(self, query: str) -> Dict[str, Any]:
        """TODO: Add docstring."""

        query_lower = query.lower()

        # 
        financial_keywords = [
            "financial", "finance", "investment", "market", "stock", "earnings",
            "financial analysis", "financial report", "market analysis", "valuation",
            "portfolio", "risk assessment", "macroeconomic"
        ]

        # 
        report_keywords = [
            "report", "analysis", "summary", "review", "insights",
            "research", "evaluation", "trends", "benchmark"
        ]

        # PPT
        ppt_keywords = [
            "ppt", "slide", "presentation", "deck", "slide deck"
        ]

        # 
        financial_score = sum(1 for kw in financial_keywords if kw in query_lower)
        report_score = sum(1 for kw in report_keywords if kw in query_lower)
        ppt_score = sum(1 for kw in ppt_keywords if kw in query_lower)

        # 
        if re.search(r'\b(ppt|presentation|slide)\b', query_lower):
            ppt_score += 5

        if re.search(r'\b(report|analysis|summary|review)\b', query_lower):
            report_score += 3

        if re.search(r'\b(financial|finance|investment|market|risk|portfolio)\b', query_lower):
            financial_score += 4

        # 
        max_score = max(financial_score, report_score, ppt_score)

        if max_score == 0:
            # 
            return {
                "output_type": "report",
                "confidence": 0.5,
                "reason": "",
                "detection_method": "rule_based"
            }

        # 
        total_score = financial_score + report_score + ppt_score
        confidence = max_score / total_score if total_score > 0 else 0.5

        if financial_score == max_score:
            output_type = "financial_analysis"
            reason = f"financial_analysis (: {financial_score})"
        elif ppt_score == max_score:
            output_type = "ppt"
            reason = f"PPT (: {ppt_score})"
        else:
            output_type = "report"
            reason = f" (: {report_score})"

        return {
            "output_type": output_type,
            "confidence": min(confidence, 0.95),
            "reason": reason,
            "detection_method": "rule_based",
            "scores": {
                "financial_analysis": financial_score,
                "report": report_score,
                "ppt": ppt_score
            }
        }

    async def _llm_based_detection(self, query: str) -> Dict[str, Any]:
        """基于LLM的输出类型检测"""

        # 尝试从YAML加载提示词
        try:
            prompt = self.prompt_manager.get_prompt(
                "agents/output_type_detector/system",
                detection_task="根据用户查询判断输出类型",
                user_query=query
            )
        except (KeyError, Exception) as e:
            logger.warning(f"[{self.name}] 加载YAML提示词失败，使用硬编码提示词: {e}")
            # 硬编码提示词（中文版本）
            prompt = """你是一个专业的输出类型检测智能体，擅长根据用户的查询意图，准确判断用户期望的输出类型。

## 核心职责
1. **意图分析**: 深度理解用户的真实需求
2. **类型判断**: 判断用户想要的输出类型
3. **置信度评估**: 评估判断的置信度

## 输出类型

### 1. 报告类 (report)
   - 综合分析、市场研究、趋势报告
   - 需要数据支撑和专业分析
   - 示例: "AI大模型市场分析报告"、"竞品对比报告"

### 2. 财务分析类 (financial_analysis)
   - 金融数据研究、投资分析、市场趋势判断
   - 需要金融指标、行业洞察和结论建议
   - 示例: "上市公司财务分析"、"行业趋势投资机会分析"

### 3. PPT类 (ppt)
   - 演示文稿、幻灯片制作
   - 需要结构化展示
   - 示例: "制作项目汇报PPT"、"创建产品发布幻灯片"

## 用户查询

{user_query}

## 输出要求

请按照以下JSON格式输出检测结果：

```json
{
  "output_type": "report | financial_analysis | ppt",
  "confidence": 0.95,
  "reason": "判断依据说明",
  "sub_type": "具体子类型（如适用）"
}
```

## 注意事项

- output_type 只允许 "report"、"financial_analysis"、"ppt" 三种值
- confidence 取值范围 0.0-1.0
- reason 简要说明判断依据

"""

        try:
            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                prompt,
                ""
            )

            # 解析JSON响应
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # 
                if "output_type" in result and result["output_type"] in ["report", "financial_analysis", "ppt"]:
                    result["detection_method"] = "llm_based"
                    logger.info(
                        f"[{self.name}] LLM: {result['output_type']} "
                        f"(: {result.get('confidence', 0.8):.2f})"
                    )
                    return result

            # 
            logger.warning(f"[{self.name}] LLM")
            return {
                "output_type": "report",
                "confidence": 0.6,
                "reason": "LLM",
                "detection_method": "fallback"
            }

        except Exception as e:
            logger.error(f"[{self.name}] LLM: {e}")
            return {
                "output_type": "report",
                "confidence": 0.5,
                "reason": f": {str(e)}",
                "detection_method": "error_fallback"
            }

