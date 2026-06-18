"""
Fiction Outline Generator Agent
"""
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
import json
import re

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager


class FictionOutlineGenerator:
    """小说大纲生成智能体，负责基于小说元素设计完整的故事大纲"""

    def __init__(self, llm_manager: LLMManager, prompt_manager: PromptManager):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = "FictionOutlineGenerator"

    async def generate_outline(
        self,
        query: str,
        elements: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成小说大纲"""

        logger.info(f"[{self.name}] Starting outline generation")

        try:
            # 构建 prompt
            outline_prompt = self._build_outline_prompt(query, elements, requirements)

            # 调用 LLM
            client = self.llm_manager.get_client("default")
            response = await client.simple_chat(
                outline_prompt,
                system_prompt=""
            )

            # 解析响应
            outline = self._parse_outline_response(response)

            # 验证和优化
            outline = self._validate_and_optimize(outline, elements, requirements)

            logger.info(f"[{self.name}] Outline generated with {len(outline['chapters'])} chapters")

            return {
                "outline": outline,
                "total_chapters": len(outline["chapters"]),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"[{self.name}] Generation failed: {e}")
            return {
                "outline": self._get_fallback_outline(elements, requirements),
                "total_chapters": 0,
                "status": "error",
                "error": str(e)
            }

    def _build_outline_prompt(
        self,
        query: str,
        elements: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> str:
        """构建设计 prompt，优先从 YAML 加载，fallback 到硬编码内容。"""

        genre = requirements.get("genre", "")
        length = requirements.get("length", "short")
        constraints = requirements.get("constraints", [])

        # 格式化小说元素
        elements_summary = self._format_elements(elements)

        # 计算章节数
        chapter_count = self._get_chapter_count(length)

        # 尝试从 YAML 加载 prompt
        try:
            yaml_prompt = self.prompt_manager.get_prompt(
                "agents/fiction/outline_generator",
                outline_task=f"生成{genre}小说大纲",
                genre=genre,
                target_length=length,
                chapter_count=chapter_count
            )
            # 追加用户需求和元素信息
            user_prompt = f"""

## 用户需求
小说主题: {query}
类型: {genre}
篇幅: {length} ({chapter_count}章)
约束条件: {', '.join(constraints) if constraints else '无'}

## 小说元素

{elements_summary}

{self._get_genre_outline_requirements(genre, constraints)}

## 输出要求

请按以下 JSON 格式输出小说大纲：

```json
{{
  "total_chapters": {chapter_count},
  "estimated_words": {chapter_count * 1000},
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "第一章标题",
      "summary": "章节内容摘要",
      "key_events": ["事件1", "事件2"],
      "character_development": "角色发展说明",
      "pacing": "快/中/慢",
      "word_count_estimate": 1000
    }}
  ],
  "plot_threads": [
    {{
      "name": "主线/副线名称",
      "description": "情节线描述",
      "resolution": "如何收束"
    }}
  ],
  "major_plot_points": {{
    "inciting_incident": "激发事件",
    "first_plot_turn": "第一个转折点",
    "midpoint": "中点转折",
    "second_plot_turn": "第二个转折点",
    "climax": "高潮",
    "resolution": "结局"
  }},
  "foreshadowing_notes": ["伏笔1", "伏笔2"]
}}
```
"""
            return yaml_prompt + user_prompt
        except (KeyError, Exception) as e:
            logger.debug(f"FictionOutlineGenerator: Failed to load YAML prompt: {e}, using fallback")

        # Fallback 到原有硬编码 prompt
        prompt = f"""# 小说大纲生成任务

## 创作主题
小说主题: {query}

## 创作要求
- **类型**: {genre}
- **篇幅**: {length} (共 {chapter_count} 章)
- **约束**: {', '.join(constraints) if constraints else ''}

## 小说元素

{elements_summary}

## 章节结构设计

请设计以下章节结构：

### 基础结构
1. 开篇章: 引入世界、主角、核心冲突
2. 发展章: 展开情节、深化角色
3. 转折章: 重大事件改变故事走向
4. 高潮章: 矛盾激化、情感爆发
5. 收尾章: 解决冲突、留下余韵

### 情节线设计
- **主线情节 (1条)**: 核心冲突的发展
- **副线情节 (1-2条)**: 辅助主线，丰富故事
- **伏笔铺设**: 埋下伏笔，后文呼应

## 类型特定要求

{self._get_genre_outline_requirements(genre, constraints)}

## 输出格式

请输出 JSON 格式：

```json
{{
  "title": "小说标题",
  "synopsis": "故事梗概",
  "chapters": [
    {{
      "id": 1,
      "title": "第一章标题",
      "writing_points": "写作要点",
      "key_scenes": ["关键场景1", "关键场景2"],
      "characters_involved": ["角色A", "角色B"],
      "suspense": "悬念设置",
      "word_count": 1000
    }}
  ]
}}
```
"""
        return prompt

    def _get_genre_outline_requirements(self, genre: str, constraints: List[str]) -> str:
        """获取类型特定的大纲要求"""

        requirements_map = {
            "科幻": """
### 科幻类型大纲要求

- **科技线**: 科技发展与冲突
- **探索线**: 探索未知世界
- **悬念铺设**: 层层揭示真相

### 节奏安排
- 第一幕: 科技引入，世界观建立
- 第二幕: 科技冲突，危机升级
- 第三幕: 科技决战，意义升华
""",
            "悬疑": """
### 悬疑类型大纲要求

- **谜题线**: 核心谜题的逐步揭示
- **推理线**: 侦探/主角的推理过程
- **误导线**: 干扰线索的布置

### 节奏安排
- 第一幕: 谜题呈现，读者参与
- 第二幕: 线索收集，误导与真相交织
- 第三幕: 真相大白，反转收尾
""",
            "言情": """
### 言情类型大纲要求

- **感情线**: 感情的萌发与发展
- **冲突线**: 阻碍感情的因素
- **和解线**: 误会的解开

### 节奏安排
- 第一幕: 相遇，感情萌芽
- 第二幕: 误解与冲突，感情波折
- 第三幕: 和解，感情升华
"""
        }

        return requirements_map.get(genre, "")

    def _get_chapter_count(self, length: str) -> int:
        """获取章节数量"""
        length_map = {
            "short": 5,
            "medium": 12,
            "long": 30
        }
        return length_map.get(length, 5)

    def _format_elements(self, elements: Dict[str, Any]) -> str:
        """格式化小说元素"""

        formatted = []

        # 世界观设置
        world_setting = elements.get("world_setting", {})
        if world_setting:
            formatted.append(f"**时间背景**: {world_setting.get('time_period', '')}")
            formatted.append(f"**地点背景**: {world_setting.get('location', '')}")
            formatted.append(f"**社会结构**: {world_setting.get('social_structure', '')}")
            formatted.append(f"**氛围**: {world_setting.get('atmosphere', '')}")

        # 角色
        characters = elements.get("characters", [])
        if characters:
            formatted.append(f"\n**角色列表** ({len(characters)} 个):")
            for char in characters[:6]:
                name = char.get("name", "")
                role = char.get("role", "")
                traits = ", ".join(char.get("core_traits", []))
                formatted.append(f"  - {name} ({role}): {traits}")

        # 核心冲突
        main_conflict = elements.get("main_conflict", "")
        if main_conflict:
            formatted.append(f"\n**核心冲突**: {main_conflict}")

        # 情节大纲
        plot_outline = elements.get("plot_outline", {})
        if plot_outline:
            formatted.append(f"\n**情节大纲**:")
            formatted.append(f"  - 开端: {plot_outline.get('beginning', '')}")
            formatted.append(f"  - 发展: {plot_outline.get('development', '')}")
            formatted.append(f"  - 高潮: {plot_outline.get('climax', '')}")
            formatted.append(f"  - 结局: {plot_outline.get('ending', '')}")

        # 主题
        themes = elements.get("themes", [])
        if themes:
            formatted.append(f"\n**主题**: {', '.join(themes)}")

        return "\n".join(formatted)

    def _parse_outline_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应，优先从 markdown 代码块中提取 JSON，兜底用正则贪婪匹配。"""

        try:
            # 策略1：尝试从 markdown ```json ``` 代码块中提取
            code_block_match = re.search(
                r'```json\s*\n?(.*?)\n?```', response, re.DOTALL
            )
            if code_block_match:
                json_str = code_block_match.group(1).strip()
                outline = json.loads(json_str)
                if "chapters" in outline and isinstance(outline["chapters"], list):
                    return outline

            # 策略2：直接解析整个响应（去掉首尾空白）
            try:
                outline = json.loads(response.strip())
                if "chapters" in outline and isinstance(outline["chapters"], list):
                    return outline
            except json.JSONDecodeError:
                pass

            # 策略3：非贪婪匹配第一个 {...} 块
            json_match = re.search(r'\{[\s\S]*?\}', response)
            if json_match:
                outline = json.loads(json_match.group())
                if "chapters" in outline and isinstance(outline["chapters"], list):
                    return outline

            logger.warning(f"[{self.name}] JSON parsing failed, using defaults")
            return self._get_default_outline()

        except Exception as e:
            logger.error(f"[{self.name}] Parse error: {e}")
            return self._get_default_outline()

    def _validate_and_optimize(
        self,
        outline: Dict[str, Any],
        elements: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证和优化大纲"""

        chapters = outline.get("chapters", [])

        # 验证章节数量
        target_count = self._get_chapter_count(requirements.get("length", "short"))

        # 补充章节编号和字数
        for i, chapter in enumerate(chapters):
            if "id" not in chapter and "chapter_number" not in chapter:
                chapter["chapter_number"] = i + 1
            if "word_count" not in chapter and "word_count_estimate" not in chapter:
                chapter["word_count_estimate"] = 1000

        outline["chapters"] = chapters

        return outline

    def _get_default_outline(self) -> Dict[str, Any]:
        """获取默认大纲"""
        return {
            "title": "未命名小说",
            "synopsis": "待续",
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "第一章",
                    "summary": "待定",
                    "key_events": ["待定"],
                    "character_development": "待定",
                    "pacing": "中",
                    "word_count_estimate": 1000
                }
            ]
        }

    def _get_fallback_outline(
        self,
        elements: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取备用大纲"""
        return self._get_default_outline()
