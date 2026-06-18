"""
PPT - PPT
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager
from ..base import BaseAgent, AgentConfig


class SlideContentGenerator(BaseAgent):
    """PPT - """

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None
    ):
        config = AgentConfig(
            name="PPT",
            description="PPT",
            llm_config_name="slide_content_generator",
            temperature=0.7,
            max_tokens=2000
        )
        super().__init__(llm_manager, prompt_manager, config)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseAgent"""
        return await self.generate_slide_content(
            slide_outline=input_data.get("slide_outline", {}),
            style=input_data.get("style", "business"),
            available_content=input_data.get("available_content", []),
            context=input_data.get("context")
        )

    async def generate_slide_content(
        self,
        slide_outline: Dict[str, Any],
        style: str,
        available_content: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        PPT

        Args:
            slide_outline: 
            style: PPT
            available_content: 
            context: 

        Returns:
            {
                "slide_number": 1,
                "type": "cover",
                "title": "",
                "subtitle": "",
                "content": {
                    "points": ["1", "2"],
                    "details": {"1": ""},
                    "visuals": [{"type": "image/chart", "description": "..."}]
                }
            }
        """
        try:
            slide_number = slide_outline.get("slide_number")
            slide_type = slide_outline.get("type", "content")

            logger.info(f"[{self.name}]  {slide_number}  (: {slide_type})")

            # 
            if slide_type == "cover":
                result = await self._generate_cover_slide(slide_outline, style)
            elif slide_type == "conclusion":
                result = await self._generate_conclusion_slide(slide_outline, style, context)
            else:  # content / section
                result = await self._generate_content_slide(
                    slide_outline, style, available_content, context
                )

            return result

        except Exception as e:
            logger.error(f"[{self.name}] : {e}")
            return self._get_fallback_slide(slide_outline)

    async def _generate_cover_slide(
        self,
        slide_outline: Dict[str, Any],
        style: str
    ) -> Dict[str, Any]:
        """TODO: Add docstring."""
        return {
            "slide_number": slide_outline.get("slide_number", 1),
            "type": "cover",
            "title": slide_outline.get("title", ""),
            "subtitle": "",
            "content": {
                "points": [],
                "details": {},
                "visuals": []
            }
        }

    async def _generate_conclusion_slide(
        self,
        slide_outline: Dict[str, Any],
        style: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成总结页。"""

        slide_number = slide_outline.get("slide_number", 1)
        key_points = slide_outline.get("key_points", [])

        # 尝试从 YAML 加载 prompt
        try:
            system_prompt = self.prompt_manager.get_prompt(
                "agents/ppt/slide_content_generator",
                content_task=f"生成总结页内容",
                slide_number=slide_number,
                slide_type="conclusion",
                style=style
            )
        except (KeyError, Exception):
            system_prompt = f"你是PPT幻灯片内容生成专家，擅长生成{style}风格的总结页"

        user_prompt = f"""
## 幻灯片信息
标题: {slide_outline.get('title', '总结')}
关键要点数量: {len(key_points)}

## 要点列表
{chr(10).join([f"{i+1}. {p}" for i, p in enumerate(key_points)])}

## 要求
生成3-5个精炼的总结要点。

请输出 JSON 格式：
```json
{{
  "points": ["要点1", "要点2", "要点3"]
}}
```"""

        response = await self.get_llm_response(user_prompt, system_prompt)

        # 解析响应
        import json
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
                points = data.get("points", ["总结要点"])
            else:
                points = key_points[:3] if key_points else ["总结"]
        except:
            points = key_points[:3] if key_points else ["总结"]

        return {
            "slide_number": slide_outline.get("slide_number"),
            "type": "conclusion",
            "title": slide_outline.get("title", ""),
            "subtitle": "",
            "content": {
                "points": points,
                "details": {},
                "visuals": []
            }
        }

    async def _generate_content_slide(
        self,
        slide_outline: Dict[str, Any],
        style: str,
        available_content: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成内容页。"""

        title = slide_outline.get("title", "")
        key_points = slide_outline.get("key_points", [])
        content_density = slide_outline.get("content_density", "medium")
        slide_number = slide_outline.get("slide_number", 1)

        # 内容密度指南
        density_guides = {
            "minimal": "1-2个要点，适合演讲",
            "medium": "3-5个要点，平衡展示",
            "detailed": "6+个要点，适合阅读"
        }

        # 提取相关内容
        relevant_content = self._extract_relevant_content(title, available_content)

        # 尝试从 YAML 加载 prompt
        try:
            system_prompt = self.prompt_manager.get_prompt(
                "agents/ppt/slide_content_generator",
                content_task=f"生成内容页内容",
                slide_number=slide_number,
                slide_type="content",
                style=style
            )
        except (KeyError, Exception):
            system_prompt = f"你是PPT幻灯片内容生成专家，擅长生成{style}风格的{content_density}密度内容页"

        user_prompt = f"""
## 幻灯片信息
标题: {title}
风格: {style}
内容密度: {content_density} ({density_guides.get(content_density, '')})

## 要点
{chr(10).join([f"- {p}" for p in key_points]) if key_points else "无预设要点"}

## 参考内容
{relevant_content if relevant_content else "无参考内容"}

## 要求
请根据以上信息生成适合该幻灯片的内容要点和详细说明。

请输出 JSON 格式：
```json
{{
  "points": ["要点1", "要点2", "要点3"],
  "details": {{"要点1": "详细说明1"}},
  "visuals": [{{"type": "image/chart", "description": "建议使用的图片或图表"}}]
}}
```

注意事项：
- 内容密度: minimal 1-2个要点, medium 3-5个要点, detailed 6+个要点
- 每个要点需要配详细说明
- 建议使用可视化元素
"""

        response = await self.get_llm_response(user_prompt, system_prompt)

        # 解析响应
        import json
        import re
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = {"points": key_points, "details": {}, "visuals": []}
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}, using key_points")
            data = {"points": key_points, "details": {}, "visuals": []}

        return {
            "slide_number": slide_outline.get("slide_number"),
            "type": slide_outline.get("type", "content"),
            "title": title,
            "subtitle": "",
            "content": {
                "points": data.get("points", key_points),
                "details": data.get("details", {}),
                "visuals": data.get("visuals", [])
            }
        }

    def _extract_relevant_content(
        self,
        title: str,
        available_content: List[Dict[str, Any]],
        max_length: int = 500
    ) -> str:
        """TODO: Add docstring."""

        relevant_texts = []
        title_lower = title.lower()

        for item in available_content[:10]:  # 10
            content = item.get("full_content", item.get("snippet", ""))
            # 
            if any(word in content.lower() for word in title_lower.split() if len(word) > 2):
                relevant_texts.append(content[:300])

        combined = "\n\n".join(relevant_texts)
        return combined[:max_length] if combined else ""

    def _get_fallback_slide(self, slide_outline: Dict[str, Any]) -> Dict[str, Any]:
        """TODO: Add docstring."""
        return {
            "slide_number": slide_outline.get("slide_number"),
            "type": slide_outline.get("type", "content"),
            "title": slide_outline.get("title", ""),
            "subtitle": "",
            "content": {
                "points": slide_outline.get("key_points", ["..."]),
                "details": {},
                "visuals": []
            }
        }
