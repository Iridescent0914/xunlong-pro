"""
报告大纲生成智能体
"""
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import re

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager


class OutlineGenerator:
    """报告大纲生成智能体，负责根据用户需求和搜索结果生成完整的研究报告大纲"""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = ""

    async def generate_outline(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        synthesis_results: Optional[Dict[str, Any]] = None,
        report_type: str = "comprehensive",
        refined_subtasks: Optional[List[Dict[str, Any]]] = None  # NEW
    ) -> Dict[str, Any]:
        """生成研究报告大纲"""

        logger.info(f"[{self.name}] 开始生成大纲 (类型: {report_type})")

        # NEW: Log if using refined subtasks
        if refined_subtasks:
            logger.info(f"[{self.name}] 使用优化后的子任务: {len(refined_subtasks)} 个")

        try:
            # 构建 prompt
            outline_prompt = self._build_outline_prompt(
                query, search_results, synthesis_results, report_type
            )

            # 调用 LLM
            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                outline_prompt,
                system_prompt=""
            )

            # 解析响应
            outline = self._parse_outline_response(response)

            # 验证和优化
            outline = self._validate_and_optimize_outline(outline, report_type)

            logger.info(f"[{self.name}] 大纲生成完成，共 {len(outline['sections'])} 个章节")

            return {
                "outline": outline,
                "total_sections": len(outline["sections"]),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"[{self.name}] 大纲生成失败: {e}")
            return {
                "outline": self._get_fallback_outline(report_type),
                "total_sections": 0,
                "status": "error",
                "error": str(e)
            }

    def _build_outline_prompt(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        synthesis_results: Optional[Dict[str, Any]],
        report_type: str
    ) -> str:
        """构建设计 prompt，优先从 YAML 加载，fallback 到硬编码内容。"""

        # 构建搜索结果摘要
        results_summary = self._summarize_search_results(search_results[:10])

        # 构建综合摘要
        synthesis_summary = ""
        if synthesis_results:
            if isinstance(synthesis_results, dict):
                synthesis_summary = synthesis_results.get("report_content", "")[:500]
            elif isinstance(synthesis_results, str):
                synthesis_summary = synthesis_results[:500]

        # 尝试从 YAML 加载 prompt
        try:
            yaml_prompt = self.prompt_manager.get_prompt(
                "agents/report/outline_generator",
                outline_task=f"根据用户需求生成{report_type}类型报告的大纲",
                report_type=report_type,
                topic=query
            )
            # 追加用户需求和搜索结果信息
            user_prompt = f"""

## 用户需求
{query}

## 报告类型
{report_type}

## 搜索结果摘要 ({len(search_results)} 条)
{results_summary}

## 综合研究摘要
{synthesis_summary}

## 输出要求

请按以下 JSON 格式输出报告大纲：

```json
{{
  "title": "报告标题",
  "sections": [
    {{
      "id": 1,
      "title": "章节标题",
      "requirements": "章节写作要求",
      "suggested_sources": ["相关来源1", "相关来源2"],
      "word_count": 500,
      "importance": 0.9
    }}
  ]
}}
```

## 报告类型参考

- **comprehensive** (综合报告): 全面覆盖主题的各个方面，需要多角度分析，500-800字/章节
- **daily** (每日简报): 聚焦当天或近期的最新动态，简洁明了，300-500字/章节
- **analysis** (专题分析): 针对特定主题的深入分析，400-600字/章节
- **research** (研究报告): 学术性和专业性较强的研究报告，600-1000字/章节

## 输出约束

- 章节数: 3-6 个
- 每个章节包含: id, title, requirements, suggested_sources, word_count, importance
- importance 范围: 0.0-1.0
"""
            return yaml_prompt + user_prompt
        except (KeyError, Exception) as e:
            logger.debug(f"OutlineGenerator: YAML prompt 加载失败: {e}，使用 fallback")

        # Fallback 到硬编码 prompt
        prompt = f"""# 报告大纲生成任务

## 用户需求
{query}

## 报告类型
{report_type}

## 搜索结果摘要
### 搜索结果 ({len(search_results)} 条)
{results_summary}

### 综合研究摘要
{synthesis_summary}

## 大纲设计要求



1. **标题**: 根据用户需求生成报告标题
2. **章节**: 设计 3-6 个章节
3. **结构**:
   - id: 章节编号
   - title: 章节标题
   - requirements: 写作要求
   - suggested_sources: 建议参考资料
   - word_count: 预估字数
   - importance: 重要性 0.0-1.0

## 报告类型参考

- **comprehensive** (综合报告): 
  - 全面覆盖主题的各个方面
  - 需要多角度、多维度的分析
  - 适合深度研究和决策参考
  - 字数: 500-800字/章节

- **daily** (每日简报): 
  - 聚焦当天或近期的最新动态
  - 简洁明了，突出重点
  - 适合快速了解行业动态
  - 字数: 300-500字/章节

- **analysis** (专题分析): 
  - 针对特定主题的深入分析
  - 需要数据和案例支撑
  - 字数: 400-600字/章节

- **research** (研究报告): 
  - 学术性和专业性较强
  - 需要充分论证
  - 字数: 600-1000字/章节

## 输出格式

请输出 JSON 格式：

```json
{{
  "title": "报告标题",
  "sections": [
    {{
      "id": 1,
      "title": "章节标题",
      "requirements": "章节写作要求",
      "suggested_sources": ["相关来源1", "相关来源2"],
      "word_count": 500,
      "importance": 0.9
    }}
  ]
}}
```

注意事项:
- 确保章节标题清晰明确
- requirements 描述要包含主要写作方向
- suggested_sources 可以参考搜索结果中的来源
- word_count 根据报告类型合理分配
"""

        return prompt

    def _summarize_search_results(self, results: List[Dict[str, Any]]) -> str:
        """总结搜索结果"""
        if not results:
            return ""

        summaries = []
        for i, result in enumerate(results[:10], 1):
            title = result.get("title", "")
            url = result.get("url", "")
            content_preview = result.get("content", "")[:100]

            summaries.append(f"{i}. {title}\n   URL: {url}\n   摘要: {content_preview}...")

        return "\n\n".join(summaries)

    def _parse_outline_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                outline = json.loads(json_str)

                # 验证必需字段
                if "title" in outline and "sections" in outline:
                    return outline

            logger.warning(f"[{self.name}] JSON 解析失败")
            return self._get_fallback_outline("comprehensive")

        except Exception as e:
            logger.error(f"[{self.name}] 解析错误: {e}")
            return self._get_fallback_outline("comprehensive")

    def _validate_and_optimize_outline(
        self,
        outline: Dict[str, Any],
        report_type: str
    ) -> Dict[str, Any]:
        """验证和优化大纲"""

        sections = outline.get("sections", [])

        # 章节数量检查
        if len(sections) < 3:
            logger.warning(f"[{self.name}] 章节数量不足 ({len(sections)})，补充默认章节")
            sections = self._add_missing_sections(sections, report_type)

        if len(sections) > 6:
            logger.warning(f"[{self.name}] 章节数量过多 ({len(sections)})，截断至6个")
            sections = sections[:6]

        # 补充缺失字段
        for i, section in enumerate(sections):
            # 章节编号
            if "id" not in section:
                section["id"] = i + 1

            # 章节标题
            if "title" not in section or not section["title"]:
                section["title"] = f"第{i+1}章"

            # 写作要求
            if "requirements" not in section or not section["requirements"]:
                section["requirements"] = f"{outline.get('title', '')}的{section['title']}部分"

            # 字数
            if "word_count" not in section:
                section["word_count"] = 500

            # 重要性
            if "importance" not in section:
                section["importance"] = 1.0 / len(sections)

            # 建议来源
            if "suggested_sources" not in section:
                section["suggested_sources"] = []

        outline["sections"] = sections

        return outline

    def _add_missing_sections(
        self,
        sections: List[Dict[str, Any]],
        report_type: str
    ) -> List[Dict[str, Any]]:
        """补充缺失的章节"""

        default_sections = {
            "comprehensive": ["背景介绍", "现状分析", "趋势预测", "案例研究", "总结建议"],
            "daily": ["今日要闻", "热点事件", "专家观点"],
            "analysis": ["问题定义", "原因分析", "影响评估", "对策建议"],
            "research": ["文献综述", "理论框架", "研究方法", "数据分析", "结论与展望"]
        }

        template = default_sections.get(report_type, default_sections["comprehensive"])

        # 如果没有章节，使用默认模板
        if not sections:
            return [
                {
                    "id": i + 1,
                    "title": title,
                    "requirements": f"撰写{title}部分的内容",
                    "word_count": 500,
                    "importance": 1.0 / len(template),
                    "suggested_sources": []
                }
                for i, title in enumerate(template)
            ]

        return sections

    def _get_fallback_outline(self, report_type: str) -> Dict[str, Any]:
        """获取备用大纲"""

        default_outlines = {
            "comprehensive": {
                "title": "综合研究报告",
                "sections": [
                    {
                        "id": 1,
                        "title": "背景介绍",
                        "requirements": "介绍报告主题的背景信息",
                        "word_count": 300,
                        "importance": 0.15,
                        "suggested_sources": []
                    },
                    {
                        "id": 2,
                        "title": "现状分析",
                        "requirements": "分析当前情况和主要特征",
                        "word_count": 800,
                        "importance": 0.35,
                        "suggested_sources": []
                    },
                    {
                        "id": 3,
                        "title": "趋势预测",
                        "requirements": "基于数据分析未来发展趋势",
                        "word_count": 700,
                        "importance": 0.30,
                        "suggested_sources": []
                    },
                    {
                        "id": 4,
                        "title": "总结建议",
                        "requirements": "总结主要发现并提出建议",
                        "word_count": 300,
                        "importance": 0.20,
                        "suggested_sources": []
                    }
                ]
            },
            "daily": {
                "title": "每日简报",
                "sections": [
                    {
                        "id": 1,
                        "title": "今日要闻",
                        "requirements": "汇总当天最重要的新闻",
                        "word_count": 300,
                        "importance": 0.25,
                        "suggested_sources": []
                    },
                    {
                        "id": 2,
                        "title": "热点分析",
                        "requirements": "深入分析2-3个热点话题",
                        "word_count": 500,
                        "importance": 0.50,
                        "suggested_sources": []
                    },
                    {
                        "id": 3,
                        "title": "明日展望",
                        "requirements": "预测明日可能的发展",
                        "word_count": 200,
                        "importance": 0.25,
                        "suggested_sources": []
                    }
                ]
            }
        }

        return default_outlines.get(report_type, default_outlines["comprehensive"])
