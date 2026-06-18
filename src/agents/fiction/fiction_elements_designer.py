"""
Fiction Elements Designer Agent
"""
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import re

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager


class FictionElementsDesigner:
    """小说元素设计智能体，负责根据用户需求设计小说的核心元素"""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = "FictionElementsDesigner"

    async def design_elements(
        self,
        query: str,
        requirements: Dict[str, Any],
        search_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """设计小说核心元素"""

        logger.info(f"[{self.name}] Starting elements design")

        try:
            # 构建 prompt
            design_prompt = self._build_design_prompt(query, requirements, search_results)

            # 调用 LLM
            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                design_prompt,
                system_prompt=""
            )

            # 解析响应
            elements = self._parse_elements_response(response)

            # 验证和优化
            elements = self._validate_and_optimize(elements, requirements)

            logger.info(f"[{self.name}] Elements design completed")

            return {
                "elements": elements,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"[{self.name}] Design failed: {e}")
            return {
                "elements": self._get_fallback_elements(requirements),
                "status": "error",
                "error": str(e)
            }

    def _build_design_prompt(
        self,
        query: str,
        requirements: Dict[str, Any],
        search_results: Optional[List[Dict[str, Any]]]
    ) -> str:
        """构建设计 prompt，优先从 YAML 加载，fallback 到硬编码内容。"""

        genre = requirements.get("genre", "")
        length = requirements.get("length", "short")
        constraints = requirements.get("constraints", [])
        target_audience = requirements.get("target_audience", "general")

        # 构建参考资料
        references = ""
        if search_results:
            references = self._format_references(search_results[:5])

        # 尝试从 YAML 加载 prompt
        try:
            yaml_prompt = self.prompt_manager.get_prompt(
                "agents/fiction/elements_designer",
                design_task=f"设计一个{genre}小说",
                genre=genre,
                target_audience=target_audience
            )
            # 追加参考资料和用户需求
            user_prompt = f"""

## 参考资料
{references if references else "无参考资料"}

## 用户需求
小说主题: {query}
类型: {genre}
篇幅: {length} ({self._get_length_desc(length)})
约束条件: {', '.join(constraints) if constraints else '无'}

{self._get_genre_specific_requirements(genre, constraints)}

## 输出要求

请按以下 JSON 格式输出小说元素设计：

```json
{{
  "title": "小说标题",
  "world_setting": {{
    "time_period": "时间背景",
    "location": "地点背景",
    "social_structure": "社会结构",
    "unique_rules": ["独特规则1", "独特规则2"],
    "atmosphere": "整体氛围描述"
  }},
  "characters": [
    {{
      "name": "角色名",
      "role": "protagonist/antagonist/supporting",
      "core_traits": ["特质1", "特质2"],
      "background": "背景故事",
      "motivation": "核心动机",
      "growth_arc": "成长弧线"
    }}
  ],
  "main_conflict": "核心冲突描述",
  "plot_outline": {{
    "beginning": "开端",
    "development": "发展",
    "climax": "高潮",
    "ending": "结局"
  }},
  "themes": ["主题1", "主题2"],
  "style_notes": "风格备注"
}}
```
"""
            return yaml_prompt + user_prompt
        except (KeyError, Exception) as e:
            logger.debug(f"FictionElementsDesigner: Failed to load YAML prompt: {e}, using fallback")

        # Fallback 到原有硬编码 prompt
        prompt = f"""# 小说元素设计任务

## 创作主题
小说主题: {query}

## 创作要求
- **类型**: {genre}
- **篇幅**: {length} ({self._get_length_desc(length)})
- **约束**: {', '.join(constraints) if constraints else ''}

## 参考资料
{references if references else ""}

## 设计任务

请设计以下元素：

### 1. 时间设定 (Time)
   - 时代背景
   - 时间跨度
   - 关键时间点

### 2. 地点设定 (Place)
   - 主要场景
   - 次要场景
   - 空间关系

### 3. 角色设定 (Characters)
   - 主要角色 3-5 个
   - 每个角色的背景、性格、动机

### 4. 情节设定 (Plot)
   - 核心冲突
   - 起因经过
   - 高潮结局

### 5. 环境设定 (Environment)
   - 社会环境
   - 自然环境
   - 氛围营造

### 6. 主题设定 (Theme)
   - 核心主题
   - 深层寓意
   - 情感基调

## 类型特定要求

{self._get_genre_specific_requirements(genre, constraints)}

## 输出格式

请输出 JSON 格式：

```json
{{
  "title": "小说标题",
  "world_setting": {{
    "time_period": "时间背景",
    "location": "地点背景",
    "social_structure": "社会结构",
    "unique_rules": ["独特规则1", "独特规则2"],
    "atmosphere": "整体氛围描述"
  }},
  "characters": [
    {{
      "name": "角色名",
      "role": "protagonist/antagonist/supporting",
      "core_traits": ["特质1", "特质2"],
      "background": "背景故事",
      "motivation": "核心动机",
      "growth_arc": "成长弧线"
    }}
  ],
  "main_conflict": "核心冲突描述",
  "plot_outline": {{
    "beginning": "开端",
    "development": "发展",
    "climax": "高潮",
    "ending": "结局"
  }},
  "themes": ["主题1", "主题2"],
  "style_notes": "风格备注"
}}
```
"""
        return prompt

    def _get_genre_specific_requirements(self, genre: str, constraints: List[str]) -> str:
        """获取类型特定的要求"""

        requirements_map = {
            "科幻": """
### 科幻类型特定要求

- **科技设定**: 核心科技是什么，原理是什么
- **未来世界**: 社会结构如何变化
- **技术边界**: 科技的局限在哪里
- **人文思考**: 科技对人性影响
- **世界观规则**: 世界的物理规则
""",
            "悬疑": """
### 悬疑类型特定要求

- **悬念设计**: 核心谜题是什么
- **线索布局**: 如何埋设线索
- **误导设置**: 如何误导读者
- **反转设计**: 何时揭示真相
""",
            "言情": """
### 言情类型特定要求

- **感情线**: 核心情感是什么
- **冲突设计**: 感情障碍是什么
- **人物关系**: 复杂的情感纠葛
- **结局走向**: 圆满/开放式结局
""",
            "奇幻": """
### 奇幻类型特定要求

- **魔法体系**: 魔法的原理和限制
- **种族设定**: 存在的种族和势力
- **世界构造**: 地理和政治格局
- **力量层级**: 角色实力体系
"""
        }

        return requirements_map.get(genre, "")

    def _get_length_desc(self, length: str) -> str:
        """获取篇幅描述"""
        length_map = {
            "short": "短篇 (5000-2万字)",
            "medium": "中篇 (2-5万字)",
            "long": "长篇 (5万字以上)"
        }
        return length_map.get(length, "")

    def _format_references(self, search_results: List[Dict[str, Any]]) -> str:
        """格式化参考资料"""
        formatted = []
        for i, result in enumerate(search_results, 1):
            title = result.get("title", "")
            content = result.get("content", "")[:300]
            formatted.append(f"### 参考 {i}: {title}\n{content}...\n")
        return "\n".join(formatted)

    def _parse_elements_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""

        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                elements = json.loads(json_match.group())
                # 验证必需字段
                required_keys = ["world_setting", "characters", "main_conflict", "plot_outline"]
                if all(key in elements for key in required_keys):
                    return elements

            logger.warning(f"[{self.name}] JSON parsing failed, using defaults")
            return self._get_default_elements()

        except Exception as e:
            logger.error(f"[{self.name}] Parse error: {e}")
            return self._get_default_elements()

    def _validate_and_optimize(
        self,
        elements: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证和优化元素"""

        # 验证角色数量
        if not elements.get("characters") or len(elements["characters"]) == 0:
            elements["characters"] = [
                {
                    "name": "默认主角",
                    "role": "protagonist",
                    "core_traits": ["勇敢", "善良"],
                    "background": "普通人",
                    "motivation": "追求理想",
                    "growth_arc": "成长蜕变"
                }
            ]

        return elements

    def _get_default_elements(self) -> Dict[str, Any]:
        """获取默认元素"""
        return {
            "title": "未命名小说",
            "world_setting": {
                "time_period": "当代",
                "location": "城市",
                "social_structure": "现代社会",
                "unique_rules": [],
                "atmosphere": "现实主义"
            },
            "characters": [
                {
                    "name": "主角",
                    "role": "protagonist",
                    "core_traits": ["勇敢"],
                    "background": "普通人",
                    "motivation": "追求理想",
                    "growth_arc": "成长蜕变"
                }
            ],
            "main_conflict": "待定",
            "plot_outline": {
                "beginning": "待定",
                "development": "待定",
                "climax": "待定",
                "ending": "待定"
            },
            "themes": ["待定"],
            "style_notes": "待定"
        }

    def _get_fallback_elements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """获取备用元素"""
        return self._get_default_elements()
