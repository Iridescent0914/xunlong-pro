"""查询优化智能体 - 将用户原始查询转换为高效的搜索策略。"""

import json
import re
from typing import Dict, Any
from loguru import logger

from .base import BaseAgent, AgentConfig
from ..llm import LLMManager, PromptManager


class QueryOptimizerAgent(BaseAgent):
    """ - """
    
    def __init__(
        self, 
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None
    ):
        config = AgentConfig(
            name="",
            description="",
            llm_config_name="query_optimizer",
            temperature=0.3,
            max_tokens=2000
        )
        
        super().__init__(llm_manager, prompt_manager, config)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """优化搜索查询，将用户原始查询转换为高效的搜索策略。"""
        try:
            query = input_data.get("query", "")
            context = input_data.get("context", {})
            query_context = context.get("description", "")

            logger.info(f"[{self.name}] 优化查询: {query}")

            # 从 YAML 加载 system prompt（包含角色定义、分析框架、输出格式）
            system_prompt = self.get_prompt(
                "agents/query_optimizer/system",
                optimization_task=f"优化搜索查询: {query}",
                user_query=query,
                query_context=query_context,
                search_engine="duckduckgo"
            )

            # 构建详细的 user prompt，充分利用 YAML 中的指导框架
            user_prompt = f"""## 任务
请分析并优化以下搜索查询，生成高效的搜索策略。

## 原始查询
"{query}"

## 查询上下文（可选）
{query_context if query_context else "无特殊上下文"}

## 输出要求
请严格按照以下 JSON 格式输出优化结果，确保所有字段都填写完整：

```json
{{
  "original_query": "{query}",
  "query_intent": "查询意图分类（信息查找/问题解答/比较分析/趋势研究/其他）",
  "entities": ["实体1", "实体2"],
  "optimized_queries": [
    {{
      "query": "优化后的查询1（更精准、更具体的表述）",
      "priority": "high",
      "search_type": "comprehensive",
      "expected_results": "预期结果类型"
    }},
    {{
      "query": "优化后的查询2（从另一角度的表述）",
      "priority": "medium",
      "search_type": "specific",
      "expected_results": "预期结果类型"
    }}
  ],
  "keywords": {{
    "primary": ["核心关键词1", "核心关键词2"],
    "secondary": ["次要关键词1"],
    "synonyms": ["同义词1", "近义词1"],
    "related": ["相关词汇1"]
  }},
  "search_strategy": {{
    "approach": "搜索方法说明",
    "filters": ["过滤条件"],
    "time_range": "时间范围（如最近一周/一个月/不限）"
  }}
}}
```

## 优化原则
1. **精准匹配**: 确保查询与用户意图精准匹配
2. **覆盖全面**: 考虑查询的多个维度和角度
3. **效率优先**: 优先生成高效的搜索查询
4. **结果导向**: 以获得高质量结果为目标

请直接输出 JSON 结果："""

            # LLM
            response = await self.get_llm_response(user_prompt, system_prompt)

            # JSON
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 从响应中提取 JSON
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {
                        "intent_analysis": "信息查找",
                        "optimized_keywords": [query],
                        "search_strategy": "综合搜索",
                        "expected_result_type": "综合信息",
                        "raw_response": response
                    }
            
            # 补充必要字段
            result["original_query"] = query
            result["optimized_query"] = (
                result.get("optimized_queries", [{}])[0].get("query", query)
                if result.get("optimized_queries")
                else result.get("optimized_keywords", [query])[0] if result.get("optimized_keywords") else query
            )

            logger.info(f"[{self.name}] 优化结果: {result.get('optimized_query', query)}")

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
                    "original_query": input_data.get("query", ""),
                    "optimized_query": input_data.get("query", ""),
                    "intent_analysis": "信息查找",
                    "optimized_keywords": [input_data.get("query", "")],
                    "search_strategy": "综合搜索",
                    "expected_result_type": "综合信息"
                }
            }