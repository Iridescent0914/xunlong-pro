"""



"""

from typing import Dict, Any, List, Optional
from loguru import logger
import json
import re

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager
from ..base import BaseAgent, AgentConfig


class DataVisualizer(BaseAgent):
    """ - """

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager = None
    ):
        config = AgentConfig(
            name="",
            description="",
            llm_config_name="data_visualizer",
            temperature=0.3,  #
            max_tokens=3000
        )
        super().__init__(llm_manager, prompt_manager, config)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """

        Args:
            input_data: {
                "content": "",
                "title": ""
            }

        Returns:
            {
                "status": "success/error",
                "enhanced_content": "",
                "visualizations": [
                    {
                        "type": "table/chart",
                        "title": "",
                        "data": {...},
                        "markdown": "Markdown",
                        "html": "HTML"
                    }
                ]
            }
        """
        try:
            content = input_data.get("content", "")
            title = input_data.get("title", "")

            if not content:
                return {
                    "status": "error",
                    "message": "",
                    "enhanced_content": content,
                    "visualizations": []
                }

            logger.info(f"[{self.name}] ...")

            # LLM
            system_prompt = self._get_system_prompt(
                visualization_task="从文本中提取可可视化数据并生成图表建议",
                content=content,
                title=title
            )
            user_prompt = self._build_user_prompt(content, title)

            response = await self.get_llm_response(user_prompt, system_prompt)

            # LLM
            viz_result = self._parse_visualization_response(response)

            if not viz_result["visualizations"]:
                logger.info(f"[{self.name}] ")
                return {
                    "status": "success",
                    "enhanced_content": content,
                    "visualizations": []
                }

            #
            visualizations = []
            for viz in viz_result["visualizations"]:
                generated_viz = await self._generate_visualization(viz)
                if generated_viz:
                    visualizations.append(generated_viz)

            logger.info(
                f"[{self.name}]  {len(visualizations)}  "
                f"({sum(1 for v in visualizations if v['type'] == 'table')} , "
                f"{sum(1 for v in visualizations if v['type'] == 'chart')} )"
            )

            # HTMLcontent
            # Markdown
            return {
                "status": "success",
                "enhanced_content": content,  #
                "visualizations": visualizations
            }

        except Exception as e:
            logger.error(f"[{self.name}] : {e}")
            return {
                "status": "error",
                "message": str(e),
                "enhanced_content": input_data.get("content", ""),
                "visualizations": []
            }

    def _get_system_prompt(self, visualization_task: str = "", content: str = "", title: str = "") -> str:
        """获取系统提示词，优先从YAML加载，失败则使用硬编码提示词。"""
        if self.prompt_manager:
            try:
                prompt = self.prompt_manager.get_prompt(
                    "agents/data_visualizer/system",
                    visualization_task=visualization_task,
                    content=content,
                    title=title
                )
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[{self.name}] 从YAML加载提示词失败，使用硬编码提示词: {e}")

        # 硬编码的中文提示词作为后备
        return """你是一个专业的数据可视化智能体，擅长从文本内容中提取数据，设计合适的图表来增强内容的可读性和说服力。

## 核心职责
1. **数据提取**: 从文本中识别和提取可量化信息
2. **数据整理**: 整理提取的数据为结构化格式
3. **图表选择**: 根据数据特点选择最合适的图表类型
4. **可视化建议**: 生成图表配置建议

## 图表选择指南
### 图表类型及适用场景
1. **柱状图**: 适用于比较不同类别的数量
2. **折线图**: 适用于展示随时间变化的趋势
3. **饼图**: 适用于展示占比关系

## 输出格式
请按照以下JSON格式输出可视化建议：
{
  "visualizations": [
    {
      "type": "table/bar/line/pie",
      "title": "图表标题",
      "data": {
        // 根据类型不同，结构不同
      },
      "position": "after_paragraph_X"
    }
  ]
}

## 增强原则
1. **适度使用**: 不要过度可视化，选择关键数据
2. **准确呈现**: 确保图表准确反映数据
3. **清晰说明**: 图表要有清晰的标题和说明
4. **视觉协调**: 图表风格要与整体内容协调
"""

    def _build_user_prompt(self, content: str, title: str = "") -> str:
        """TODO: Add docstring."""
        prompt = f"""

"""
        if title:
            prompt += f"{title}\n\n"

        prompt += f"""
{content}

JSONvisualizations"""

        return prompt

    def _parse_visualization_response(self, response: str) -> Dict[str, Any]:
        """LLM"""
        try:
            # JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
            else:
                return {"visualizations": []}
        except Exception as e:
            logger.error(f": {e}")
            return {"visualizations": []}

    async def _generate_visualization(
        self,
        viz_spec: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """TODO: Add docstring."""
        try:
            viz_type = viz_spec.get("type", "table")
            title = viz_spec.get("title", "")
            data = viz_spec.get("data", {})

            if viz_type == "table":
                return self._generate_table(title, data)
            elif viz_type in ["bar", "line", "pie"]:
                return self._generate_chart(viz_type, title, data)
            else:
                logger.warning(f": {viz_type}")
                return None

        except Exception as e:
            logger.error(f": {e}")
            return None

    def _generate_table(
        self,
        title: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """TODO: Add docstring."""
        headers = data.get("headers", [])
        rows = data.get("rows", [])

        if not headers or not rows:
            return None

        # Markdown
        md_lines = [f"**{title}**\n"]
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in rows:
            md_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        markdown = "\n".join(md_lines)

        # HTML
        html_lines = [f'<div class="data-table">']
        html_lines.append(f'<h4>{title}</h4>')
        html_lines.append('<table>')
        html_lines.append('<thead><tr>')
        for header in headers:
            html_lines.append(f'<th>{header}</th>')
        html_lines.append('</tr></thead>')
        html_lines.append('<tbody>')

        for row in rows:
            html_lines.append('<tr>')
            for cell in row:
                html_lines.append(f'<td>{cell}</td>')
            html_lines.append('</tr>')

        html_lines.append('</tbody></table></div>')

        html = "\n".join(html_lines)

        return {
            "type": "table",
            "title": title,
            "data": data,
            "markdown": markdown,
            "html": html
        }

    def _generate_chart(
        self,
        chart_type: str,
        title: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ECharts"""
        import uuid
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"

        # ECharts
        echarts_option = self._build_echarts_option(chart_type, title, data)

        if not echarts_option:
            return None

        # Markdown
        markdown = f"**{title}** []\n\n> {self._get_chart_type_name(chart_type)}"

        # HTMLECharts- DOMContentLoaded
        html = f'''<div class="data-chart">
<div id="{chart_id}" style="width: 100%; height: 400px;"></div>
<script>
(function() {{
  function initChart() {{
    if (typeof echarts === 'undefined') {{
      console.error('ECharts library not loaded for {chart_id}');
      return;
    }}
    var chartDom = document.getElementById('{chart_id}');
    if (!chartDom) {{
      console.error('Chart container not found: {chart_id}');
      return;
    }}
    var chart = echarts.init(chartDom);
    var option = {json.dumps(echarts_option, ensure_ascii=False)};
    chart.setOption(option);
    window.addEventListener('resize', function() {{
      chart.resize();
    }});
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initChart);
  }} else {{
    initChart();
  }}
}})();
</script>
</div>'''

        return {
            "type": "chart",
            "chart_type": chart_type,
            "title": title,
            "data": data,
            "markdown": markdown,
            "html": html,
            "chart_id": chart_id
        }

    def _build_echarts_option(
        self,
        chart_type: str,
        title: str,
        data: Dict[str, Any]
    ) -> Optional[Dict]:
        """ECharts"""
        try:
            if chart_type == "bar":
                return {
                    "title": {"text": title},
                    "tooltip": {},
                    "xAxis": {"type": "category", "data": data.get("labels", [])},
                    "yAxis": {"type": "value"},
                    "series": [{
                        "type": "bar",
                        "data": data.get("values", [])
                    }]
                }
            elif chart_type == "line":
                return {
                    "title": {"text": title},
                    "tooltip": {},
                    "xAxis": {"type": "category", "data": data.get("labels", [])},
                    "yAxis": {"type": "value"},
                    "series": [{
                        "type": "line",
                        "data": data.get("values", [])
                    }]
                }
            elif chart_type == "pie":
                pie_data = [
                    {"name": label, "value": value}
                    for label, value in zip(
                        data.get("labels", []),
                        data.get("values", [])
                    )
                ]
                return {
                    "title": {"text": title},
                    "tooltip": {},
                    "series": [{
                        "type": "pie",
                        "radius": "50%",
                        "data": pie_data
                    }]
                }
            else:
                return None
        except Exception as e:
            logger.error(f"ECharts: {e}")
            return None

    def _get_chart_type_name(self, chart_type: str) -> str:
        """TODO: Add docstring."""
        names = {
            "bar": "",
            "line": "",
            "pie": ""
        }
        return names.get(chart_type, "")

    def _insert_visualizations(
        self,
        content: str,
        visualizations: List[Dict[str, Any]]
    ) -> str:
        """TODO: Add docstring."""
        if not visualizations:
            return content

        #
        enhanced_content = content + "\n\n"

        for viz in visualizations:
            # MarkdownHTML
            enhanced_content += "\n\n" + viz["markdown"] + "\n\n"

        return enhanced_content
