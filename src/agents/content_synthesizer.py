"""内容综合智能体 - 将多个来源的信息整合成连贯、全面的报告。"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from .base import BaseAgent, AgentConfig
from ..llm import LLMManager, PromptManager


class ContentSynthesizerAgent(BaseAgent):
    """内容综合智能体，负责将分散的信息整合成连贯、全面的报告。"""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None
    ):
        config = AgentConfig(
            name="内容综合智能体",
            description="将多个来源的信息整合成连贯、全面的报告",
            llm_config_name="content_synthesizer",
            temperature=0.7,
            max_tokens=6000
        )

        super().__init__(llm_manager, prompt_manager, config)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """综合多个来源的信息，生成连贯的报告内容。"""
        try:
            query = input_data.get("query", "")
            search_results = input_data.get("search_results", [])
            analysis_results = input_data.get("analysis_results", {})
            data_analysis_results = input_data.get("data_analysis_results") or {}

            logger.info(f"[{self.name}] 综合内容: {query}")
            if data_analysis_results.get("status") == "success":
                logger.info(
                    f"[{self.name}] 含金融数据分析: "
                    f"{len(data_analysis_results.get('key_findings', []))} 条结论"
                )

            # 从 YAML 加载 system prompt
            system_prompt = self.get_prompt(
                "agents/content_synthesizer/system",
                synthesis_task=f"综合内容: {query}",
                target_audience="通用读者",
                report_type="综合报告"
            )

            da_key_findings = data_analysis_results.get("key_findings", [])
            da_metrics = data_analysis_results.get("metrics", {})
            da_methodology = data_analysis_results.get("methodology", "")

            # 准备综合数据
            synthesis_data = {
                "query": query,
                "search_results_count": len(search_results),
                "key_insights": analysis_results.get("result", {}).get("key_insights", []),
                "content_themes": analysis_results.get("result", {}).get("content_themes", []),
                "data_analysis_findings": da_key_findings,
                "data_analysis_metrics": da_metrics,
                "data_analysis_methodology": da_methodology,
                "top_results": []
            }

            # 取前 5 个结果
            for i, result in enumerate(search_results[:5]):
                synthesis_data["top_results"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content_summary": (result.get("content", "") or result.get("snippet", ""))[:800] + "..." if result.get("content") or result.get("snippet") else ""
                })

            # 构建详细的 user prompt
            user_prompt = f"""## 任务
请基于以下搜索结果和分析信息，生成一份连贯、全面的综合报告。

## 用户查询
"{query}"

## 分析结果摘要
{json.dumps({
    "key_insights": synthesis_data["key_insights"],
    "content_themes": synthesis_data["content_themes"],
    "results_count": synthesis_data["search_results_count"]
}, ensure_ascii=False, indent=2)}

## 金融数据分析结果（数字不可改写，须原样引用 value）
{json.dumps({
    "methodology": synthesis_data["data_analysis_methodology"],
    "metrics": synthesis_data["data_analysis_metrics"],
    "key_findings": synthesis_data["data_analysis_findings"],
}, ensure_ascii=False, indent=2) if da_key_findings or da_metrics else "（无结构化数据分析）"}

## 搜索结果来源
{json.dumps(synthesis_data["top_results"], ensure_ascii=False, indent=2)}

## 输出要求
请严格按照以下 JSON 格式输出综合报告：

```json
{{
  "executive_summary": "执行摘要（100-200字，概括核心内容和主要结论）",
  "main_findings": ["主要发现1", "主要发现2", "主要发现3"],
  "report_content": "详细报告内容（Markdown格式，800-2000字，包含以下部分）：\n\n## 执行摘要\n[摘要内容]\n\n## 详细分析\n[详细分析内容]\n\n## 关键洞察\n[关键洞察]\n\n## 结论与建议\n[结论和建议]",
  "detailed_analysis": "详细分析内容（Markdown格式）",
  "conclusions": ["结论1", "结论2"],
  "sources": [
    {{"title": "来源标题1", "url": "来源URL1"}},
    {{"title": "来源标题2", "url": "来源URL2"}}
  ]
}}
```

## 综合原则
1. **信息融合**: 将多个来源的信息无缝融合，避免简单堆砌
2. **逻辑重构**: 重新组织信息的逻辑结构，层次分明
3. **内容优化**: 优化表达方式，提高可读性
4. **观点平衡**: 平衡不同观点，呈现全面视角
5. **引用标注**: 重要数据和观点需标注来源
6. **数据分析章节**: 若上方有 key_findings / metrics，须在 report_content 中包含「## 数据分析」小节，**不得改写 metrics 与 key_findings 中的数值**

请直接输出 JSON 结果："""

            # LLM
            response = await self.get_llm_response(user_prompt, system_prompt)

            # JSON
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试从响应中提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {
                        "report_content": response,
                        "executive_summary": "",
                        "main_findings": [],
                        "detailed_analysis": response,
                        "conclusions": [],
                        "sources": [r.get("url", "") for r in search_results[:5]]
                    }

            # 补充必要字段
            if "report_content" not in result:
                result["report_content"] = result.get("detailed_analysis", response)

            result["query"] = query
            result["synthesis_timestamp"] = datetime.now().isoformat()
            result["sources_count"] = len(search_results)
            has_da = data_analysis_results.get("status") == "success"
            result["data_analysis_included"] = has_da
            if has_da:
                result["data_analysis_summary"] = {
                    "metrics": da_metrics,
                    "key_findings_count": len(da_key_findings),
                    "charts_count": len(data_analysis_results.get("charts", [])),
                }
            result["analysis_quality"] = (
                "good"
                if analysis_results.get("status") == "success" or has_da
                else "limited"
            )

            logger.info(f"[{self.name}] 综合完成，字数: {len(result.get('report_content', ''))}")

            return {
                "status": "success",
                "agent": self.name,
                "result": result
            }

        except Exception as e:
            logger.error(f"[{self.name}] 错误: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "result": {
                    "report_content": f"'{input_data.get('query', '')}' 综合失败: {e}",
                    "executive_summary": "",
                    "main_findings": [],
                    "detailed_analysis": "",
                    "conclusions": [],
                    "sources": [],
                    "query": input_data.get("query", ""),
                    "sources_count": 0,
                    "analysis_quality": "failed"
                }
            }

    async def synthesize_subtask(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        analysis_results: Dict[str, Any],
        subtask_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        综合单个子任务的内容。
        基于搜索结果生成针对特定子任务的精炼、有组织的摘要。
        """
        try:
            logger.info(f"[{self.name}] 子任务内容综合: '{query}' ({len(search_results)} 条结果)")

            if not search_results:
                return {
                    "status": "warning",
                    "agent": self.name,
                    "result": {
                        "synthesized_content": f"未找到与 '{query}' 相关的内容",
                        "key_points": [],
                        "summary": "",
                        "sources": []
                    }
                }

            # 从 YAML 加载 system prompt
            system_prompt = self.get_prompt(
                "agents/content_synthesizer/system",
                synthesis_task=f"综合子任务内容: {query}",
                target_audience="通用读者",
                report_type="子任务摘要"
            )

            # 提取分析结果中的关键信息
            analysis_data = analysis_results.get("result", {})
            key_insights = analysis_data.get("key_insights", [])
            content_themes = analysis_data.get("content_themes", [])
            quality_score = analysis_data.get("quality_score", 0.5)

            # 准备内容片段
            content_snippets = []
            sources = []
            for i, result in enumerate(search_results[:5]):
                content = result.get("content", "") or result.get("snippet", "")
                if content:
                    content_snippets.append({
                        "source": result.get("title", f"来源 {i+1}"),
                        "url": result.get("url", ""),
                        "content": content[:800] + "..." if len(content) > 800 else content
                    })
                    sources.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", "")
                    })

            # 构建详细的 user prompt
            user_prompt = f"""## 任务
请基于以下搜索结果，为指定的子任务生成精炼、有组织的综合内容。

## 子任务信息
- **子任务标题**: {subtask_context.get('title', query)}
- **子任务描述**: {subtask_context.get('description', '')}
- **用户查询**: {query}

## 分析摘要
- **关键洞察**: {', '.join(key_insights) if key_insights else '无'}
- **内容主题**: {', '.join(content_themes) if content_themes else '无'}
- **质量评分**: {quality_score:.2f}

## 搜索结果来源
{json.dumps(content_snippets, ensure_ascii=False, indent=2)}

## 输出要求
请严格按照以下 JSON 格式输出综合结果：

```json
{{
  "synthesized_content": "综合后的内容（Markdown格式，800-1500字，包含：\\n## 概述\\n[简要说明]\\n\\n## 详细分析\\n[详细分析内容]\\n\\n## 关键要点\\n- 要点1\\n- 要点2\\n- 要点3]",
  "key_points": ["关键要点1", "关键要点2", "关键要点3"],
  "summary": "2-3句话的简要总结",
  "sources": [
    {{"title": "来源标题", "url": "来源URL"}}
  ],
  "confidence": 0.85
}}
```

## 综合原则
1. **信息融合**: 将多个来源的信息无缝融合，避免简单堆砌
2. **逻辑重构**: 重新组织信息的逻辑结构，层次分明
3. **内容优化**: 优化表达方式，提高可读性
4. **观点平衡**: 平衡不同观点，呈现全面视角
5. **引用标注**: 重要数据和观点需标注来源

请直接输出 JSON 结果："""

            # Get LLM synthesis
            response = await self.get_llm_response(user_prompt, system_prompt)

            # 解析 JSON 响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {
                        "synthesized_content": response,
                        "key_points": key_insights[:3] if key_insights else [],
                        "summary": response[:200] + "..." if len(response) > 200 else response,
                        "sources": sources[:3],
                        "confidence": 0.7
                    }

            # 添加元数据
            result["subtask_id"] = subtask_context.get("id", "")
            result["subtask_title"] = subtask_context.get("title", query)
            result["sources_count"] = len(sources)
            result["synthesized_at"] = datetime.now().isoformat()
            result["word_count"] = len(result.get("synthesized_content", ""))

            # 确保 sources 字段存在
            if "sources" not in result:
                result["sources"] = sources[:5]

            logger.info(f"[{self.name}] 子任务完成: '{query}' ({result.get('word_count', 0)} 字)")

            return {
                "status": "success",
                "agent": self.name,
                "result": result
            }

        except Exception as e:
            logger.error(f"[{self.name}] 子任务失败: '{query}': {e}")
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
                "result": {
                    "synthesized_content": f"'{query}' 综合失败: {e}",
                    "key_points": [],
                    "summary": "",
                    "sources": [],
                    "subtask_id": subtask_context.get("id", ""),
                    "subtask_title": subtask_context.get("title", query),
                    "sources_count": 0,
                    "word_count": 0,
                    "confidence": 0.0
                }
            }