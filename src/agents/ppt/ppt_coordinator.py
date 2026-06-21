"""
PPT - PPT
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
from datetime import datetime
from pydantic import BaseModel, Field

from ...llm.manager import LLMManager
from ...llm.prompts import PromptManager
from .outline_generator import PPTOutlineGenerator
from .slide_content_generator import SlideContentGenerator
from .multi_slide_generator import MultiSlidePPTGenerator, create_slide_data
from .design_coordinator import DesignCoordinator, DesignSpec


# ==========  ==========
class PPTOutline(BaseModel):
    """PPT - """
    title: str = Field(description="PPT")
    subtitle: Optional[str] = Field(default=None, description="")
    colors: Dict[str, str] = Field(description="{primary, accent, background, text, secondary}")
    pages: List[Dict[str, Any]] = Field(description="{slide_number, page_type, topic, key_points, has_chart}")


# ==========  ==========
class ColorScheme(BaseModel):
    """TODO: Add docstring."""
    primary: str = Field(description="#ff4757")
    accent: str = Field(description="")
    background: str = Field(description="")
    text: str = Field(description="")
    secondary: str = Field(description="")


class SlideDesign(BaseModel):
    """TODO: Add docstring."""
    layout_strategy: str = Field(description=": center_text|left_right_split|grid_cards|big_numbers|top_bottom|custom")
    visual_style: str = Field(description="''''''")
    color_usage: str = Field(description="'+''+'")


class SlideContent(BaseModel):
    """TODO: Add docstring."""
    title: Optional[str] = Field(default=None, description="")
    main_points: List[str] = Field(description="3-5")
    data_items: Optional[List[Dict[str, str]]] = Field(default=None, description="[{'label':'','value':'4850'}]")
    detail_text: Optional[str] = Field(default=None, description="")
    chart: Optional[Dict[str, Any]] = Field(default=None, description="typedata")


class Slide(BaseModel):
    """ - """
    slide_number: int = Field(description="")
    design: SlideDesign = Field(description="")
    content: SlideContent = Field(description="")


class PPTData(BaseModel):
    """PPT"""
    title: str = Field(description="PPT")
    subtitle: Optional[str] = Field(default=None, description="")
    colors: ColorScheme = Field(description="")
    slides: List[Slide] = Field(description="")


class PPTCoordinator:
    """PPT - PPT"""

    def __init__(
        self,
        llm_manager: LLMManager,
        prompt_manager: PromptManager
    ):
        self.llm_manager = llm_manager
        self.prompt_manager = prompt_manager
        self.name = "PPT"

        #
        self.outline_generator = PPTOutlineGenerator(llm_manager, prompt_manager)
        self.slide_content_generator = SlideContentGenerator(llm_manager, prompt_manager)
        self.multi_slide_generator = MultiSlidePPTGenerator(llm_manager, prompt_manager)

        # 设计协调器 - 生成全局设计规范
        llm_client = llm_manager.get_client("outline_generator")
        self.design_coordinator = DesignCoordinator(llm_client, prompt_manager)

    async def generate_ppt_v2(
        self,
        topic: str,
        search_results: List[Dict[str, Any]],
        ppt_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PPT ()

        Phase 1: OutlineAgent
        Phase 2: NPageAgentHTML
        Phase 3: AssemblerAgentPPT
        """
        logger.info(f"[{self.name}] PPT: {topic}")

        try:
            style = ppt_config.get('style', 'business')
            slides = ppt_config.get('slides', 10)
            speech_notes = ppt_config.get('speech_notes')  # 

            # Phase 1: 
            logger.info(f"[{self.name}] Phase 1: PPT")
            outline = await self._generate_outline_v2(topic, search_results, style, slides)

            # Phase 2: HTML
            logger.info(f"[{self.name}] Phase 2: {len(outline['pages'])}")
            page_results = await self._parallel_generate_pages(
                outline=outline,
                search_results=search_results,
                style=style,
                speech_scene=speech_notes  # 
            )

            # Phase 3: PPT
            logger.info(f"[{self.name}] Phase 3: PPT")
            html_content = self._assemble_ppt_v2(outline, page_results)

            # 
            speech_notes_data = None
            if speech_notes:
                speech_notes_data = []
                for page in page_results:
                    if "speech_notes" in page:
                        speech_notes_data.append({
                            "slide_number": page["slide_number"],
                            "speech_notes": page["speech_notes"]
                        })

            result = {
                "status": "success",
                "ppt": {
                    "title": outline['title'],
                    "subtitle": outline.get('subtitle', ''),
                    "colors": outline['colors'],
                    "slides": page_results,  # html_contentspeech_notes
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "style": style,
                        "slide_count": len(page_results),
                        "has_speech_notes": bool(speech_notes)
                    }
                },
                "html_content": html_content
            }

            # 
            if speech_notes_data:
                result["speech_notes"] = speech_notes_data

            return result

        except Exception as e:
            logger.error(f"[{self.name}] PPT: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }

    async def generate_ppt_v3(
        self,
        topic: str,
        search_results: List[Dict[str, Any]],
        ppt_config: Dict[str, Any],
        output_dir: Path,
        data_analysis_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成多页HTML PPT (新架构 V3)

        使用多页HTML架构，每张幻灯片是独立的HTML文件
        复用V2的PageAgent来生成详细内容

        Args:
            topic: PPT主题
            search_results: 搜索结果
            ppt_config: PPT配置
                {
                    'style': 'ted/business/academic/creative/simple',
                    'slides': 10,
                    'theme': 'default/blue/red/green/purple'
                }
            output_dir: 输出目录

        Returns:
            {
                "status": "success/error",
                "ppt_dir": "PPT目录路径",
                "total_slides": 10,
                "slide_files": [...],
                "index_page": "导航页路径",
                "presenter_page": "演示模式页路径"
            }
        """
        logger.info(f"[{self.name}] 生成多页HTML PPT (V3): {topic}")
        logger.info(f"[{self.name}] PPT配置: {ppt_config}")

        try:
            style = ppt_config.get('style', 'business')
            slides_count = ppt_config.get('slides', 10)
            theme = ppt_config.get('theme', 'default')

            # Phase 1: 生成大纲
            logger.info(f"[{self.name}] Phase 1: 生成PPT大纲 (目标{slides_count}页)")
            print(f"\n📋 正在生成PPT大纲... (目标: {slides_count}页)")
            outline = await self._generate_outline_v2(topic, search_results, style, slides_count)
            print(f"✅ 大纲生成完成！实际生成 {len(outline['pages'])} 页")

            # Phase 1.5: 生成全局设计规范 (NEW)
            logger.info(f"[{self.name}] Phase 1.5: 生成全局设计规范")
            print(f"\n🎨 正在生成全局设计规范...")
            design_spec = await self.design_coordinator.generate_design_spec(
                topic=topic,
                outline=outline,
                style=style
            )
            logger.info(f"[{self.name}] 设计规范: {design_spec.layout_style}风格, 主色{design_spec.primary_color}")
            print(f"✅ 设计规范生成完成！风格: {design_spec.layout_style}, 主色: {design_spec.primary_color}")

            # Phase 2: 使用PageAgent生成每页的详细HTML内容 (复用V2逻辑)
            total_pages = len(outline['pages'])
            logger.info(f"[{self.name}] Phase 2: 生成每页详细内容 ({total_pages} 页)")
            print(f"\n📄 正在并行生成 {total_pages} 页内容...")
            print(f"   提示: 大模型正在思考中，这可能需要几分钟时间...")
            page_results = await self._parallel_generate_pages(
                outline=outline,
                search_results=search_results,
                style=style,
                speech_scene=None,  # V3不需要演讲稿
                design_spec=design_spec  # 传递全局设计规范
            )
            success_count = sum(1 for r in page_results if r.get('html_content'))
            print(f"✅ 页面内容生成完成！成功: {success_count}/{total_pages} 页")

            # Phase 3: 将页面内容转换为幻灯片数据结构
            logger.info(f"[{self.name}] Phase 3: 构建幻灯片数据")
            print(f"\n🔧 正在构建幻灯片数据结构...")
            slides_data = self._convert_pages_to_slides_data(outline, page_results)
            slides_data = self._inject_data_analysis_slides(
                slides_data, outline, data_analysis_results
            )
            if data_analysis_results and slides_data:
                da_count = sum(1 for s in slides_data if s.get("is_data_analysis"))
                if da_count:
                    print(f"📊 已插入金融数据分析模块 {da_count} 页")
            print(f"✅ 数据结构构建完成！")

            # Phase 4: 使用MultiSlidePPTGenerator生成多页HTML PPT文件
            logger.info(f"[{self.name}] Phase 4: 生成多页HTML文件")
            print(f"\n📦 正在生成多页HTML文件和导航页面...")
            result = await self.multi_slide_generator.generate_ppt(
                slides_data=slides_data,
                ppt_config={
                    'ppt_title': outline['title'],
                    'subtitle': outline.get('subtitle', ''),
                    'colors': outline['colors'],
                    'style': style,
                    'theme': theme,
                    'author': 'SmartFin AI',
                    'date': datetime.now().strftime('%Y-%m-%d')
                },
                output_dir=output_dir
            )

            logger.info(f"[{self.name}] 多页HTML PPT生成完成")
            print(f"✅ PPT生成完成！")
            print(f"\n🎉 生成成功！")
            print(f"   📁 PPT目录: {result.get('ppt_dir')}")
            print(f"   📄 总页数: {result.get('total_slides')}")
            print(f"   🏠 导航页: {result.get('index_page')}")
            print(f"   🎬 演示页: {result.get('presenter_page')}")
            return result

        except Exception as e:
            logger.error(f"[{self.name}] 生成多页HTML PPT失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }

    def _convert_outline_to_slides_data(
        self,
        outline: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将大纲转换为幻灯片数据

        Args:
            outline: PPT大纲
            search_results: 搜索结果用于填充内容

        Returns:
            幻灯片数据列表
        """
        slides_data = []
        content_summary = self._summarize_search_results(search_results)

        for i, page in enumerate(outline['pages']):
            page_type = page.get('page_type', 'content')

            # 映射page_type到slide_type
            type_mapping = {
                'title': 'cover',
                'content': 'content',
                'section': 'content',
                'conclusion': 'summary',
                'chart': 'chart'
            }

            slide_type = type_mapping.get(page_type, 'content')

            # 构建幻灯片数据
            slide_data = {
                'slide_number': page['slide_number'],
                'type': slide_type,
                'title': page.get('topic', ''),
                'template': self._get_template_for_type(slide_type)
            }

            # 根据类型添加内容
            if slide_type == 'cover':
                slide_data['content'] = {
                    'title': outline['title'],
                    'subtitle': outline.get('subtitle', ''),
                    'author': 'SmartFin AI',
                    'date': datetime.now().strftime('%Y-%m-%d')
                }

            elif slide_type == 'toc':
                # 生成目录
                sections = []
                content_pages = [p for p in outline['pages'] if p.get('page_type') in ['section', 'content']]
                for idx, p in enumerate(content_pages[:6], 1):  # 最多6个章节
                    sections.append({
                        'number': idx,
                        'title': p.get('topic', ''),
                        'subtitle': ', '.join(p.get('key_points', [])[:2]) if p.get('key_points') else ''
                    })
                slide_data['content'] = {'sections': sections}

            elif slide_type == 'content':
                # 内容页
                key_points = page.get('key_points', [])
                slide_data['content'] = {
                    'title': page.get('topic', ''),
                    'layout': 'bullets' if len(key_points) > 0 else 'paragraph',
                    'points': key_points,
                    'details': content_summary[:500] if content_summary else ''
                }

            elif slide_type == 'chart':
                # 图表页
                slide_data['content'] = {
                    'title': page.get('topic', ''),
                    'chart_type': 'bar',
                    'categories': ['2022', '2023', '2024', '2025'],
                    'data': [100, 150, 200, 250],
                    'series_name': '数据趋势',
                    'y_axis_name': '数值'
                }

            elif slide_type == 'summary':
                # 总结页
                points = page.get('key_points', [])
                slide_data['content'] = {
                    'title': '总结',
                    'points': [{'text': p, 'icon': 'check'} for p in points] if points else [
                        {'text': '感谢观看', 'icon': 'heart'}
                    ],
                    'closing': '谢谢！'
                }

            slides_data.append(slide_data)

        return slides_data

    def _convert_pages_to_slides_data(
        self,
        outline: Dict[str, Any],
        page_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将PageAgent生成的页面HTML转换为幻灯片数据

        Args:
            outline: PPT大纲
            page_results: PageAgent生成的页面列表，每页包含html_content

        Returns:
            幻灯片数据列表
        """
        slides_data = []

        for i, page in enumerate(page_results):
            slide_number = page.get('slide_number', i + 1)
            html_content = page.get('html_content', '')
            has_error = page.get('__error__', False)

            # 从outline获取页面类型和标题
            outline_page = outline['pages'][i] if i < len(outline['pages']) else {}
            page_type = outline_page.get('page_type', 'content')
            topic = outline_page.get('topic', f'Slide {slide_number}')

            # 映射page_type到slide_type
            type_mapping = {
                'title': 'cover',
                'content': 'content',
                'section': 'content',
                'conclusion': 'summary',
                'chart': 'chart'
            }
            slide_type = type_mapping.get(page_type, 'content')

            if has_error or not html_content:
                html_content = (
                    f'<div style="display:flex;align-items:center;justify-content:center;'
                    f'height:100vh;flex-direction:column;color:#888;text-align:center">'
                    f'<div style="font-size:2em;margin-bottom:1rem">⚠</div>'
                    f'<div style="font-size:1.5em;font-weight:bold;margin-bottom:0.5rem">第 {slide_number} 页</div>'
                    f'<div style="font-size:1.2em">{topic}</div>'
                    f'<div style="margin-top:1rem;font-size:1em;color:#aaa">内容生成失败（API限流）</div>'
                    f'</div>'
                )

            # 构建幻灯片数据
            slide_data = {
                'slide_number': slide_number,
                'type': slide_type,
                'title': topic,
                'template': self._get_template_for_type(slide_type),
                # 将PageAgent生成的HTML内容直接存储
                'html_content': html_content
            }

            slides_data.append(slide_data)

        return slides_data

    def _inject_data_analysis_slides(
        self,
        slides_data: List[Dict[str, Any]],
        outline: Dict[str, Any],
        data_analysis_results: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """在结论页之前插入金融数据分析幻灯片并重新编号。"""
        from ..data_analysis.ppt_section import build_data_analysis_slides

        da_slides = build_data_analysis_slides(
            data_analysis_results,
            section_index=len(slides_data),
            colors=outline.get("colors") or {},
        )
        if not da_slides:
            return slides_data

        insert_at = len(slides_data)
        for i, page in enumerate(outline.get("pages") or []):
            if page.get("page_type") == "conclusion":
                insert_at = i
                break

        merged = slides_data[:insert_at] + da_slides + slides_data[insert_at:]
        for i, slide in enumerate(merged):
            slide["slide_number"] = i + 1
        return merged

    def _get_template_for_type(self, slide_type: str) -> str:
        """根据幻灯片类型返回模板名称"""
        template_mapping = {
            'cover': 'slide_cover.html',
            'toc': 'slide_toc.html',
            'content': 'slide_content.html',
            'chart': 'slide_chart.html',
            'summary': 'slide_summary.html'
        }
        return template_mapping.get(slide_type, 'slide_content.html')

    async def generate_ppt(
        self,
        topic: str,
        search_results: List[Dict[str, Any]],
        ppt_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        PPT

        Args:
            topic: PPT
            search_results: 
            ppt_config: PPT
                {
                    'style': 'ted/business/academic/creative/simple',
                    'slides': 10,
                    'depth': 'surface/medium/deep',
                    'theme': 'default/blue/red/green/purple'
                }

        Returns:
            {
                "status": "success/error",
                "ppt": {
                    "title": "PPT",
                    "subtitle": "",
                    "slides": [...],
                    "metadata": {...}
                },
                "html_content": "HTMLPPT"
            }
        """

        logger.info(f"[{self.name}] PPT: {topic}")
        logger.info(f"[{self.name}] PPT: {ppt_config}")

        try:
            style = ppt_config.get('style', 'business')
            logger.info(f"[{self.name}] : {style}")
            slides = ppt_config.get('slides', 10)
            depth = ppt_config.get('depth', 'medium')
            theme = ppt_config.get('theme', 'default')

            # Phase 1: 
            logger.info(f"[{self.name}] Phase 1: PPT")
            template_info = self._load_template_info(style)

            # Phase 2: LLMPPT
            logger.info(f"[{self.name}] Phase 2: PPT")
            ppt_data = await self._generate_ppt_with_template(
                topic=topic,
                style=style,
                slides=slides,
                depth=depth,
                theme=theme,
                template_info=template_info,
                search_results=search_results
            )

            # Phase 3: HTML
            logger.info(f"[{self.name}] Phase 3: HTML")
            html_content = await self._convert_to_html(ppt_data, style, theme)

            logger.info(f"[{self.name}] PPT")

            return {
                "status": "success",
                "ppt": ppt_data,
                "html_content": html_content
            }

        except Exception as e:
            logger.error(f"[{self.name}] PPT: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _load_template_info(self, style: str) -> Dict[str, Any]:
        """TODO: Add docstring."""
        from pathlib import Path
        import re

        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'html' / 'ppt'
        template_file = template_dir / f"{style}.html"

        if not template_file.exists():
            logger.warning(f": {template_file}business")
            template_file = template_dir / "business.html"

        # 
        template_content = template_file.read_text(encoding='utf-8')

        # 
        metadata_match = re.search(r'<!-- METADATA: ({.*?}) -->', template_content)
        metadata = {}
        if metadata_match:
            import json
            metadata = json.loads(metadata_match.group(1))

        # 200
        template_lines = template_content.split('\n')[:200]
        template_structure = '\n'.join(template_lines)

        return {
            "style": style,
            "name": metadata.get("name", style),
            "description": metadata.get("description", ""),
            "template_structure": template_structure,
            "metadata": metadata
        }

    async def _generate_ppt_with_template(
        self,
        topic: str,
        style: str,
        slides: int,
        depth: str,
        theme: str,
        template_info: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """PPT"""

        # 
        content_summary = self._summarize_search_results(search_results)

        # 
        system_prompt = self._build_template_aware_system_prompt(template_info, style, depth)
        user_prompt = self._build_template_aware_user_prompt(
            topic, slides, content_summary, template_info
        )

        # 
        from ...llm.client import LLMClient

        # LLM
        llm_client = self.llm_manager.get_client("outline_generator")

        # 
        ppt_result = await llm_client.get_structured_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_model=PPTData
        )

        # 
        ppt_data = ppt_result.model_dump()

        # 
        ppt_data["metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "style": style,
            "theme": theme,
            "slide_count": len(ppt_data.get("slides", [])),
            "depth": depth
        }

        logger.info(f"[{self.name}] PPT {len(ppt_data['slides'])} ")

        return ppt_data

    def _summarize_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """TODO: Add docstring."""
        summary_parts = []

        for i, result in enumerate(search_results[:15], 1):
            title = result.get("title", "")
            content = result.get("content", "")[:800]
            url = result.get("url", "")

            images = result.get("images", [])
            image_lines = ""
            if images:
                valid_images = [img for img in images if img.get("url") and img["url"].startswith("http")]
                if valid_images:
                    image_lines = "\n相关图片:\n" + "\n".join(
                        f"- {img.get('alt', 'image')}: {img['url']}" for img in valid_images[:3]
                    )

            summary_parts.append(f"{i}. {title}\n来源: {url}\n内容: {content}...\n{image_lines}\n---")

        return "\n\n".join(summary_parts)

    def _build_template_aware_system_prompt(
        self,
        template_info: Dict[str, Any],
        style: str,
        depth: str
    ) -> str:
        """TODO: Add docstring."""

        style_guides = {
            "red": """REDPPT

RED
- ****1-3
- ****3-8
- ****
- ****
- ****minimal - 

****
- ****#ff4757, #ee5a6f, #e84118
- #2d3436, #1e272e, #c23616
- 

****
1. **main_points**3-8
2. **detail_text**20
3. 3
4. 5-12


- title: "AI"
- main_points: ["", "90%", ""]
- detail_text: "GPT-3GPT-5"
""",
            "business": """PPT


- ****3-5
- ****
- ****
- ****
- ****detailed - 

****
- ****#1e3a8a, #2563eb, #3b82f6
- #60a5fa, #93c5fd
- #ffffff

****
1. **main_points**15-25
2. **detail_text******50-150
   - "50""35%"
   - "2025Q3""20258"
   - /"OpenAIGPT-4""MetaLlama"
   - "20233"
3. ****data_itemsmain_points + detail_text
4. data_items

****
```json
{{
  "title": "AI",
  "main_points": [
    "35.2%",
    "20231809",
    ""
  ],
  "detail_text": "Precedence ResearchAI2025562030361OpenAIGoogleAnthropic70%OpenAIChatGPT220221342.83288%"
}}
```

****
```json
{{
  "title": "",
  "main_points": [],  //  Businessmain_points
  "data_items": [{{"label": "", "value": "50"}}],  //  
  "detail_text": null  //  detail_text
}}
```
""",
            "academic": """PPT

- ****
- ****
- ****
- ****detailed - 


- ""
- 
""",
            "creative": """PPT

- ****
- ****
- ****
- ****medium - 
""",
            "simple": """PPT

- ****idea
- ****
- ****minimal - 
"""
        }

        template_desc = template_info.get("description", "")
        style_guide = style_guides.get(style, style_guides["business"])

        # 
        color_guides = {
            "red": """
RED- ****
- primary****#ff4757, #ee5a6f, #e84118, #c23616
- accent#2d3436, #1e272e, #c23616
- background#ffffff#f8f9fa
- text#2d3436
- secondary#636e72

****RED
""",
            "business": """
- ****
- primary****#1e3a8a, #2563eb, #3b82f6, #1d4ed8
- accent#60a5fa, #93c5fd
- background#ffffff
- text#1f2937
- secondary#6b7280

****PPT
- /AI#3b82f6, #6366f1
- +#1e3a8a, #f59e0b
- /****#f97316, #dc2626
- #0ea5e9, #14b8a6
- #3b82f6, #fb923c
""",
            "academic": """

- primary#0f172a, #065f46, #1e3a8a
- accent#f59e0b, #ea580c
- background#ffffff
- text#000000
- secondary#4b5563
""",
            "creative": """

- primary#a855f7, #ec4899, #f43f5e
- accent#06b6d4, #10b981
- background#fafafa
- text#18181b
- secondary#71717a
""",
            "simple": """

- primary#18181b, #0f172a
- accent#52525b, #64748b
- background#ffffff
- text#000000
- secondary#a1a1aa
"""
        }

        color_guide = color_guides.get(style, color_guides["business"])

        return f"""{style_guide}

# 
- {template_info.get("name")}
- {template_desc}

# 
{color_guide}

****PPT
- 
- 
- /
- 
- 
- 

# 

PPT********HTML

JSONPPT
- title: PPT
- subtitle: 
- colors:  {{
    "primary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "text": "#hex",
    "secondary": "#hex"
  }}
- slides: slide
  - slide_number: 
  - design:  {{
      "layout_strategy": "center_text|left_right_split|grid_cards|big_numbers|top_bottom|title_page|bullets|custom",
      "visual_style": "''/''/''/''/''",
      "color_usage": "'+''+'''"
    }}
  - content:  {{
      "title": "",
      "main_points": ["1", "2", "3"],
      "data_items": [
        {{"label": "", "value": ""}},  // 
        ...
      ],
      "detail_text": "",  // 
      "chart": {{  // 
        "type": "bar/line/pie/area",
        "data": {{
          "labels": ["2022", "2023", "2025"],
          "datasets": [
            {{"label": "", "data": [141, 294, 495]}}
          ]
        }},
        "title": ""
      }}
    }}

****
1. ****design""content""
2. ****
   - title_page: 
   - center_text: 
   - left_right_split: 
   - grid_cards: 
   - big_numbers: 
   - top_bottom: +
   - bullets: 
   - custom: visual_style
3. ****"3"
4. ****
5. ****data_items[{{"label":"","value":"4850"}}]
6. REDBusinessCreative
"""

    def _build_template_aware_user_prompt(
        self,
        topic: str,
        slides: int,
        content_summary: str,
        template_info: Dict[str, Any]
    ) -> str:
        """TODO: Add docstring."""

        return f"""{template_info.get('name')}PPT

# 
{topic}

# 
{slides}

# 
{content_summary}

# 
1. **{template_info.get('name')}**
2. 1layout_strategy: title_page
3. 1
4. layout_strategy: center_text

5. ****
   - RED****primary#ff4757
   - Business
     * /AI#3b82f6, #6366f1
     * /#f97316, #dc2626
     * +#1e3a8a, #f59e0b
     * #0ea5e9, #14b8a6
   - Creative#a855f7, #ec4899

6. ****
   - Business/Academic
   - evidence
   - RED/Simple

7. ****
   - RED/Simple:
     * 1-3main_points
     * 3-8
     * detail_text20
   - Business:
     * **3-5main_points**
     * **detail_text**50-150
     * data_itemsmain_points + detail_text
   - Academic:
     * 3-4main_points
     * detail_text80-150

****

JSON

**RED**
```json
{{
  "title": "AI",
  "subtitle": "",
  "colors": {{
    "primary": "#ff4757",  // 
    "accent": "#2d3436",
    "background": "#ffffff",
    "text": "#2d3436",
    "secondary": "#636e72"
  }},
  "slides": [
    {{
      "slide_number": 1,
      "design": {{"layout_strategy": "title_page", "visual_style": "", "color_usage": "+"}},
      "content": {{"title": "AI", "main_points": [], "detail_text": ""}}
    }},
    {{
      "slide_number": 2,
      "design": {{"layout_strategy": "bullets", "visual_style": "", "color_usage": "+"}},
      "content": {{"title": "", "main_points": ["", "90%", ""], "detail_text": "GPT-3GPT-5"}}
    }}
  ]
}}
```

**Business**
```json
{{
  "title": "2025",
  "subtitle": "",
  "colors": {{
    "primary": "#f97316",  // 
    "accent": "#fb923c",
    "background": "#ffffff",
    "text": "#1f2937",
    "secondary": "#6b7280"
  }},
  "slides": [
    {{
      "slide_number": 1,
      "design": {{"layout_strategy": "title_page", "visual_style": "", "color_usage": "+"}},
      "content": {{"title": "2025", "main_points": [], "detail_text": ""}}
    }},
    {{
      "slide_number": 2,
      "design": {{"layout_strategy": "bullets", "visual_style": "", "color_usage": "+"}},
      "content": {{
        "title": "",
        "main_points": [
          "2025485033.8%",
          "202630%+",
          "B65%C45%",
          "C40%"
        ],
        "detail_text": "2025"
      }}
    }},
    {{
      "slide_number": 3,
      "design": {{"layout_strategy": "bullets", "visual_style": "", "color_usage": "+"}},
      "content": {{
        "title": "",
        "main_points": [
          "2022-2025",
          "30%",
          "2026"
        ],
        "chart": {{
          "type": "bar",
          "data": {{
            "labels": ["2022", "2023", "2025", "2025E", "2026E"],
            "datasets": [
              {{"label": "", "data": [3200, 4100, 4850, 6500, 10000]}}
            ]
          }},
          "title": ""
        }},
        "detail_text": ""
      }}
    }}
  ]
}}
```

****
- ****RED
- **Businessmain_points**3-5detail_text
- **REDmain_points**3-8detail_text
- **visual_style**"+"
  * 2
  * 3
  * 4
  * 5
  * 6
  * 
- ****
  *   line
  *   bar
  *   pie
  * 2-3
"""

    async def _parallel_generate_slides(
        self,
        slide_outlines: List[Dict[str, Any]],
        style: str,
        available_content: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """TODO: Add docstring."""

        logger.info(f"[{self.name}]  {len(slide_outlines)} ")

        tasks = []
        for i, slide_outline in enumerate(slide_outlines):
            # 
            context = {}
            if i > 0:
                context["previous_slide"] = slide_outlines[i - 1]

            task = self.slide_content_generator.generate_slide_content(
                slide_outline=slide_outline,
                style=style,
                available_content=available_content,
                context=context
            )
            tasks.append(task)

        # 
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 
        slides_content = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[{self.name}]  {i+1} : {result}")
                # fallback
                slides_content.append({
                    "slide_number": i + 1,
                    "type": slide_outlines[i].get("type", "content"),
                    "title": slide_outlines[i].get("title", ""),
                    "subtitle": "",
                    "content": {
                        "points": [""],
                        "details": {},
                        "visuals": []
                    }
                })
            else:
                slides_content.append(result)

        logger.info(f"[{self.name}] ")
        return slides_content

    def _assemble_ppt(
        self,
        outline: Dict[str, Any],
        slides_content: List[Dict[str, Any]],
        topic: str,
        style: str,
        theme: str
    ) -> Dict[str, Any]:
        """PPT"""

        logger.info(f"[{self.name}] PPT")

        # 
        slides_sorted = sorted(slides_content, key=lambda x: x.get("slide_number", 0))

        ppt_data = {
            "title": outline.get("title", topic),
            "subtitle": outline.get("subtitle", ""),
            "slides": slides_sorted,
            "metadata": {
                "topic": topic,
                "style": style,
                "theme": theme,
                "slide_count": len(slides_sorted),
                "generated_at": datetime.now().isoformat(),
                "generator": "SmartFin PPT Generator"
            }
        }

        logger.info(f"[{self.name}] PPT {len(slides_sorted)} ")

        return ppt_data

    async def _convert_to_html(
        self,
        ppt_data: Dict[str, Any],
        style: str,
        theme: str
    ) -> str:
        """PPTHTML - SlideRenderAgent"""
        try:
            from .slide_render_agent import SlideRenderAgent

            logger.info(f"[{self.name}] SlideRenderAgentHTML")

            # 
            render_agent = SlideRenderAgent(colors=ppt_data.get('colors', {}))

            # 
            rendered_slides = []
            for slide_data in ppt_data.get('slides', []):
                # Slide
                slide = Slide(**slide_data)

                # RenderAgent
                rendered = render_agent.render_slide(
                    slide_number=slide.slide_number,
                    design=slide.design,
                    content=slide.content
                )

                rendered_slides.append(rendered)

            # flexible.htmlHTML
            html_content = self._build_html_from_slides(
                ppt_data=ppt_data,
                rendered_slides=rendered_slides
            )

            logger.info(f"[{self.name}] HTML")
            return html_content

        except Exception as e:
            logger.error(f"[{self.name}] HTML: {e}")
            import traceback
            traceback.print_exc()
            # HTML fallback
            return self._get_fallback_html(ppt_data)

    def _get_css_component_guide(self) -> str:
        """CSS"""
        return """# CSS
- : .text-xs/.text-xl/.text-5xl/.text-9xl, .font-bold/.font-black, .text-center
- : .text-primary/.text-white, .bg-primary/.bg-white/.gradient-primary
- : .flex/.flex-col/.flex-1, .items-center/.justify-center, .grid/.grid-cols-2/.grid-cols-3
- : .gap-4/.gap-8/.gap-16, .p-8/.p-16, .mt-4/.mb-8
- : .rounded-xl, .shadow-lg, .border-l-4, .card
- : .animate-fadeIn/.animate-slideUp
- : .w-full/.w-1\\/2, .h-full/.h-64/.h-80/.h-96"""

    async def _generate_slide_html(
        self,
        slide_data: Dict[str, Any],
        colors: Dict[str, str],
        css_guide: str,
        style: str
    ) -> str:
        """LLMHTML"""

        design = slide_data.get('design', {})
        content = slide_data.get('content', {})

        prompt = f"""HTML

# 
- : {design.get('layout_strategy', 'bullets')}
- : {design.get('visual_style', '')}
- : {design.get('color_usage', '')}

# 
- : {content.get('title', '')}
- : {content.get('main_points', [])}
- : {content.get('data_items', [])}
- : {content.get('detail_text', '')}

# 
{colors}

{css_guide}

****
1. visual_styleHTML
2. FlexGridCSS
3. PPT{style}
4. HTMLdiv<html>/<body>
5. ****

HTML
"""

        # LLMHTML
        llm_client = self.llm_manager.get_client("outline_generator")

        response = await llm_client.get_completion(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.8  # 
        )

        # HTML
        html = response.strip()
        # markdown
        if html.startswith('```html'):
            html = html[7:]
        if html.startswith('```'):
            html = html[3:]
        if html.endswith('```'):
            html = html[:-3]

        return html.strip()

    def _build_html_from_slides(
        self,
        ppt_data: Dict[str, Any],
        rendered_slides: List[Dict[str, str]]
    ) -> str:
        """flexible.htmlHTML"""
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        # 
        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'html' / 'ppt'
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template('flexible.html')

        # 
        render_data = {
            'title': ppt_data.get('title', 'PPT'),
            'subtitle': ppt_data.get('subtitle', ''),
            'colors': ppt_data.get('colors', {}),
            'slides': rendered_slides,
            'metadata': ppt_data.get('metadata', {}),
            'generated_at': ppt_data.get('metadata', {}).get('generated_at', ''),
            'generator': 'SmartFin PPT Generator'
        }

        # HTML
        html = template.render(**render_data)
        return html

    def _get_fallback_html(self, ppt_data: Dict[str, Any]) -> str:
        """fallback HTML"""
        slides_html = []
        for slide in ppt_data.get("slides", []):
            slides_html.append(f"""
<div class="slide">
    <h2>{slide.get('title', '')}</h2>
    <ul>
        {''.join(f'<li>{p}</li>' for p in slide.get('content', {}).get('points', []))}
    </ul>
</div>
""")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{ppt_data.get('title', 'PPT')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .slide {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; }}
        h2 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>{ppt_data.get('title', 'PPT')}</h1>
    {''.join(slides_html)}
</body>
</html>
"""

    async def _generate_outline_v2(
        self,
        topic: str,
        search_results: List[Dict[str, Any]],
        style: str,
        slides: int
    ) -> Dict[str, Any]:
        """
        Phase 1: PPT
        """
        content_summary = self._summarize_search_results(search_results)

        #
        prompt = f"""PPT

#
{topic}

#
{style}

#
**{slides}**

#
{content_summary[:2000]}

#
**{slides}**pages

1. **1**page_type: title
2. **1**page_type: conclusion
3. page_type: section
4. page_type: content
5. topickey_points2-4
6. has_chart: true2-3
7.
   - RED#ff4757
   - Business#3b82f6, #6366f1
   - Business#f97316, #dc2626

**{slides}pages**

JSON
{{
  "title": "PPT",
  "subtitle": "",
  "colors": {{
    "primary": "#3b82f6",
    "accent": "#6366f1",
    "background": "#ffffff",
    "text": "#1f2937",
    "secondary": "#6b7280"
  }},
  "pages": [
    {{
      "slide_number": 1,
      "page_type": "title",
      "topic": "2025",
      "key_points": [],
      "has_chart": false
    }},
    {{
      "slide_number": 2,
      "page_type": "content",
      "topic": "",
      "key_points": ["", "", ""],
      "has_chart": true
    }},
    ... ({slides - 2}pages)
    {{
      "slide_number": {slides},
      "page_type": "conclusion",
      "topic": "",
      "key_points": ["", ""],
      "has_chart": false
    }}
  ]
}}

**pages{slides}**
"""

        llm_client = self.llm_manager.get_client("outline_generator")

        # 
        outline_result = await llm_client.get_structured_response(
            prompt=prompt,
            response_model=PPTOutline
        )

        return outline_result.model_dump()

    async def _parallel_generate_pages(
        self,
        outline: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        style: str,
        speech_scene: Optional[str] = None,
        design_spec: Optional[DesignSpec] = None  # 新增: 全局设计规范
    ) -> List[Dict[str, Any]]:
        """
        Phase 2: HTML

        PageAgent
        """
        from .page_agent import PageAgent, PageSpec, GlobalContext

        # 构建全局上下文 - 如果有design_spec则使用它，否则使用outline的colors
        colors_to_use = outline['colors']
        if design_spec:
            # 使用设计规范的配色方案
            colors_to_use = {
                'primary': design_spec.primary_color,
                'secondary': design_spec.secondary_color,
                'accent': design_spec.accent_color,
                'background': design_spec.background_color,
                'text': design_spec.text_color,
                'text_secondary': design_spec.text_secondary_color
            }

        global_context = GlobalContext(
            ppt_title=outline['title'],
            style=style,
            colors=colors_to_use,
            total_slides=len(outline['pages']),
            speech_scene=speech_scene  #
        )

        #
        content_summary = self._summarize_search_results(search_results)

        # 构建CSS指南 - 如果有design_spec，则包含设计规范信息
        css_guide = self._get_css_component_guide()
        if design_spec:
            css_guide += f"""

# 全局设计规范 (IMPORTANT - 必须严格遵守!)
**配色方案:**
- 主色: {design_spec.primary_color}
- 次色: {design_spec.secondary_color}
- 强调色: {design_spec.accent_color}
- 背景色: {design_spec.background_color}
- 文字色: {design_spec.text_color}
- 次要文字色: {design_spec.text_secondary_color}

**字体规范:**
- 字体: {design_spec.font_family}
- 标题字号: {design_spec.title_font_size}
- 正文字号: {design_spec.content_font_size}

**视觉风格:**
- 布局风格: {design_spec.layout_style}
- 间距: {design_spec.spacing}
- 圆角: {design_spec.border_radius}
- 阴影: {'启用' if design_spec.use_shadows else '禁用'}
- 渐变: {'启用' if design_spec.use_gradients else '禁用'}
- 动画: {design_spec.animation_style}

**图表配色 (Chart.js使用):**
{', '.join(design_spec.chart_colors)}

**重要提示:**
所有页面必须使用以上统一的设计规范！不得自行更改颜色、字体或风格！
"""

        # PageAgent
        llm_client = self.llm_manager.get_client("outline_generator")
        page_agent = PageAgent(llm_client, css_guide)

        # 
        tasks = []
        for page_outline in outline['pages']:
            page_spec = PageSpec(**page_outline)

            task = page_agent.generate_page_html(
                page_spec=page_spec,
                global_context=global_context,
                content_data=content_summary
            )
            tasks.append(task)

        #
        logger.info(f"[{self.name}] {len(tasks)}...")

        # 使用进度显示的方式并行生成
        total = len(tasks)
        print(f"   [0/{total}] 开始生成...")

        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        #
        results = []
        success = 0
        failed = 0

        for i, result in enumerate(page_results):
            if isinstance(result, Exception):
                failed += 1
                logger.error(f"[{self.name}] {i+1}: {result}")
                print(f"   X 第{i+1}页生成失败: {str(result)[:80]}")
                # 标记为失败，不再给 fallback 内容
                results.append({
                    "slide_number": i + 1,
                    "html_content": "",
                    "__error__": True,
                    "speech_notes": None
                })
            else:
                success += 1
                page_data = {
                    "slide_number": i + 1,
                    "html_content": result.get("html_content", ""),
                }
                if "speech_notes" in result:
                    page_data["speech_notes"] = result.get("speech_notes")
                results.append(page_data)

                print(f"   V [{success}/{total}] 第{i+1}页生成完成")

        print(f"\n   生成统计: 成功 {success} 页, 失败 {failed} 页")
        return results

    def _assemble_ppt_v2(
        self,
        outline: Dict[str, Any],
        page_htmls: List[Dict[str, Any]]
    ) -> str:
        """
        Phase 3: PPT

        HTMLflexible.html
        """
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        # 
        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'html' / 'ppt'
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template('flexible.html')

        # slidesflexible.html
        slides = []
        for page in page_htmls:
            slides.append({
                'slide_number': page['slide_number'],
                'html_content': page['html_content'],
                'custom_style': ''  # 
            })

        # HTML
        html = template.render(
            title=outline['title'],
            subtitle=outline.get('subtitle', ''),
            colors=outline['colors'],
            slides=slides,
            metadata={'generated_at': datetime.now().isoformat()}
        )

        return html

    def get_status(self) -> Dict[str, Any]:
        """TODO: Add docstring."""
        return {
            "name": self.name,
            "agents": {
                "outline_generator": self.outline_generator.name,
                "slide_content_generator": self.slide_content_generator.name
            }
        }
