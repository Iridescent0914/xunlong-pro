#!/usr/bin/env python
"""
SmartFin - Financial Analysis & Content CLI
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.deep_search_agent import DeepSearchAgent
from src.utils.document_loader import load_document, LoadedDocument, DocumentLoadError


# CLI
@click.group()
@click.version_option(version="1.0.0", prog_name="SmartFin")
def cli():
    """
    SmartFin - 智能金融分析与内容生成 CLI

    支持 report / analyze / ppt / export / iterate / ask / status 子命令。
    """
    pass


def _load_user_document(input_file: Optional[Path], verbose: bool) -> Dict[str, Dict[str, object] | str]:
    """Load optional user document and return context payload."""

    if not input_file:
        return {}

    try:
        loaded: LoadedDocument = load_document(input_file)
    except DocumentLoadError as exc:
        click.echo(click.style(f" : {exc}", fg="red"))
        sys.exit(1)

    if verbose:
        meta_msg = f": {loaded.filename} ({loaded.char_length} "
        if loaded.truncated:
            meta_msg += ""
        meta_msg += ")"
        click.echo(meta_msg)

    return {
        'user_document': loaded.content,
        'user_document_meta': {
            'filename': loaded.filename,
            'suffix': loaded.suffix,
            'char_length': loaded.char_length,
            'truncated': loaded.truncated,
            'source_path': loaded.source_path
        }
    }


# ============================================================
# 
# ============================================================

@cli.command()
@click.argument('query')
@click.option('--type', '-t', 'report_type',
              type=click.Choice(['comprehensive', 'daily', 'analysis', 'research'], case_sensitive=False),
              default='comprehensive',
              help='comprehensive(), daily(), analysis(), research()')
@click.option('--depth', '-d',
              type=click.Choice(['surface', 'medium', 'deep'], case_sensitive=False),
              default='deep',
              help='surface(), medium(), deep()')
@click.option('--max-results', '-m',
              type=int,
              default=20,
              help=' (: 20)')
@click.option('--output-format', '-o',
              type=click.Choice(['html', 'md', 'markdown'], case_sensitive=False),
              default='html',
              help='html(HTML), md/markdown(Markdown)')
@click.option('--html-template',
              type=str,
              default='enhanced_professional',
              help='HTMLenhanced_professional(), academic(), technical()')
@click.option('--html-theme',
              type=str,
              default='light',
              help='HTMLlight(), dark()')
@click.option('--input-file',
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='.txt/.pdf/.docx')
@click.option('--verbose', '-v',
              is_flag=True,
              help='')
def report(query, report_type, depth, max_results, output_format, html_template, html_theme, input_file, verbose):
    """
    

    :

    \b
        SmartFin report ""
        SmartFin report "" --type analysis --depth deep -o html
        SmartFin report "" -t research -m 30 -o md -v
    """
    asyncio.run(_execute_report(query, report_type, depth, max_results, output_format, html_template, html_theme, input_file, verbose))


async def _execute_report(query: str, report_type: str, depth: str, max_results: int,
                          output_format: str, html_template: str, html_theme: str,
                          input_file: Optional[Path], verbose: bool):
    """TODO: Add docstring."""

    click.echo(click.style("\n=== SmartFin  ===\n", fg="cyan", bold=True))

    # 
    output_format = 'md' if output_format in ['markdown', 'md'] else output_format

    if verbose:
        click.echo(f": {query}")
        click.echo(f": {report_type}")
        click.echo(f": {depth}")
        click.echo(f": {max_results}")
        click.echo(f": {output_format}")
        if output_format == 'html':
            click.echo(f"HTML: {html_template}")
            click.echo(f"HTML: {html_theme}")
        click.echo()

    user_document = _load_user_document(input_file, verbose)

    try:
        agent = DeepSearchAgent()

        if verbose:
            click.echo(click.style(" ", fg="green") + "\n")

        # report
        with click.progressbar(length=100, label='') as bar:
            result = await agent.search(
                query,
                context={
                    'output_type': 'report',  # 
                    'report_type': report_type,
                    'search_depth': depth,
                    'max_results': max_results,
                    'output_format': output_format,  # 
                    'html_template': html_template,  # HTML
                    'html_theme': html_theme,  # HTML
                    **user_document
                }
            )
            bar.update(100)

        click.echo()

        # 
        _display_result(result, verbose, output_format=output_format)

    except KeyboardInterrupt:
        click.echo(click.style("\n  ", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n : {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================
# 金融数据分析
# ============================================================

@cli.command('analyze')
@click.argument('query')
@click.option('--deliverable', '-D',
              type=click.Choice(['report', 'ppt', 'none'], case_sensitive=False),
              default='report',
              help='产出物：report 综合分析报告 / ppt 演示文稿 / none 仅金融数据分析')
@click.option('--depth', '-d',
              type=click.Choice(['surface', 'medium', 'deep'], case_sensitive=False),
              default='deep',
              help='搜索深度：surface / medium / deep')
@click.option('--max-results', '-m',
              type=int,
              default=20,
              help='最大搜索结果数（默认 20）')
@click.option('--output-format', '-o',
              type=click.Choice(['html', 'md', 'markdown'], case_sensitive=False),
              default='html',
              help='报告格式（仅 --deliverable report 时有效）：html / md')
@click.option('--html-template',
              type=str,
              default='enhanced_professional',
              help='HTML 模板（仅 report + html 时有效）')
@click.option('--html-theme',
              type=str,
              default='light',
              help='HTML 主题（仅 report + html 时有效）：light / dark')
@click.option('--ppt-style', '-s',
              type=click.Choice(['ted', 'business', 'academic', 'creative', 'simple'], case_sensitive=False),
              default='business',
              help='PPT 风格（仅 --deliverable ppt 时有效）')
@click.option('--slides', '-n',
              type=int,
              default=10,
              help='PPT 页数（仅 --deliverable ppt 时有效）')
@click.option('--ppt-theme',
              type=str,
              default='default',
              help='PPT 主题（仅 --deliverable ppt 时有效）')
@click.option('--mock-search',
              is_flag=True,
              help='使用 fixtures/mock_search.json 代替真实网页搜索（联调/离线）')
@click.option('--input-file',
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='补充参考文档 .txt/.pdf/.docx')
@click.option('--verbose', '-v',
              is_flag=True,
              help='显示详细日志')
def analyze(query, deliverable, depth, max_results, output_format, html_template, html_theme,
            ppt_style, slides, ppt_theme, mock_search, input_file, verbose):
    """
    金融数据分析模式：网页搜索 + 结构化分析，可选生成报告或 PPT。

    示例：

    \b
        SmartFin analyze "分析2024年银行业营收趋势"
        SmartFin analyze "分析华为营收" --deliverable report -o html
        SmartFin analyze "分析华为营收" --deliverable ppt -s business -n 12
        SmartFin analyze "分析华为营收" --deliverable none
        SmartFin analyze "测试分析" --mock-search -v
    """
    asyncio.run(_execute_analyze(
        query, deliverable, depth, max_results, output_format, html_template, html_theme,
        ppt_style, slides, ppt_theme, mock_search, input_file, verbose,
    ))


async def _execute_analyze(
    query: str,
    deliverable: str,
    depth: str,
    max_results: int,
    output_format: str,
    html_template: str,
    html_theme: str,
    ppt_style: str,
    slides: int,
    ppt_theme: str,
    mock_search: bool,
    input_file: Optional[Path],
    verbose: bool,
):
    click.echo(click.style("\n=== SmartFin 金融数据分析 ===\n", fg="yellow", bold=True))

    deliverable = deliverable.lower()
    output_format = 'md' if output_format in ['markdown', 'md'] else output_format

    if verbose:
        click.echo(f"查询: {query}")
        click.echo(f"产出物: {deliverable}")
        click.echo(f"搜索深度: {depth}")
        click.echo(f"最大结果数: {max_results}")
        if deliverable == 'report':
            click.echo(f"报告格式: {output_format}")
            if output_format == 'html':
                click.echo(f"HTML 模板: {html_template}")
                click.echo(f"HTML 主题: {html_theme}")
        elif deliverable == 'ppt':
            click.echo(f"PPT 风格: {ppt_style}")
            click.echo(f"PPT 页数: {slides}")
            click.echo(f"PPT 主题: {ppt_theme}")
        click.echo(f"Mock 搜索: {'是' if mock_search else '否'}")
        click.echo()

    user_document = _load_user_document(input_file, verbose)

    try:
        agent = DeepSearchAgent()

        if verbose:
            label = {
                'report': '正在执行金融数据分析 + 报告生成...',
                'ppt': '正在执行金融数据分析 + PPT 生成...',
                'none': '正在执行金融数据分析（不生成报告/PPT）...',
            }.get(deliverable, '正在执行金融数据分析工作流...')
            click.echo(click.style(label, fg="green") + "\n")

        context: Dict[str, Any] = {
            'output_type': 'financial_analysis',
            'deliverable': deliverable,
            'search_depth': depth,
            'max_results': max_results,
            'use_mock_search': mock_search,
            **user_document,
        }
        if deliverable == 'report':
            context.update({
                'output_format': output_format,
                'html_template': html_template,
                'html_theme': html_theme,
            })
        elif deliverable == 'ppt':
            context['ppt_config'] = {
                'style': ppt_style,
                'slides': slides,
                'depth': depth,
                'theme': ppt_theme,
            }

        with click.progressbar(length=100, label='分析中') as bar:
            result = await agent.search(query, context=context)
            bar.update(100)

        click.echo()
        display_type = 'ppt' if deliverable == 'ppt' else 'financial_analysis'
        display_format = 'html' if deliverable == 'ppt' else output_format
        _display_result(result, verbose, output_type=display_type, output_format=display_format)

    except KeyboardInterrupt:
        click.echo(click.style("\n  ", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n : {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================
# 
# ============================================================

@cli.command()
@click.argument('topic')
@click.option('--style', '-s',
              type=click.Choice(['ted', 'business', 'academic', 'creative', 'simple'], case_sensitive=False),
              default='business',
              help='PPTted(TED), business(), academic(), creative(), simple()')
@click.option('--slides', '-n',
              type=int,
              default=10,
              help='PPT (: 10)')
@click.option('--depth', '-d',
              type=click.Choice(['surface', 'medium', 'deep'], case_sensitive=False),
              default='medium',
              help='surface(), medium(), deep()')
@click.option('--theme',
              type=str,
              default='default',
              help='default(), blue(), red(), green(), purple()')
@click.option('--speech-notes',
              type=str,
              default=None,
              help='""')
@click.option('--input-file',
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='.txt/.pdf/.docxPPT')
@click.option('--verbose', '-v',
              is_flag=True,
              help='')
def ppt(topic, style, slides, depth, theme, speech_notes, input_file, verbose):
    """
    PPT

    :

    \b
        SmartFin ppt ""
        SmartFin ppt "" --style business --slides 15
        SmartFin ppt "2025" -s ted -n 8 -v
        SmartFin ppt "" -s academic -d deep --theme blue
        SmartFin ppt "" --speech-notes "" -v
    """
    asyncio.run(_execute_ppt(topic, style, slides, depth, theme, speech_notes, input_file, verbose))


async def _execute_ppt(topic: str, style: str, slides: int, depth: str, theme: str,
                       speech_notes: str, input_file: Optional[Path], verbose: bool):
    """PPT"""

    click.echo(click.style("\n=== SmartFin PPT ===\n", fg="green", bold=True))

    if verbose:
        click.echo(f": {topic}")
        click.echo(f": {style}")
        click.echo(f": {slides}")
        click.echo(f": {depth}")
        click.echo(f": {theme}")
        if speech_notes:
            click.echo(f": {speech_notes}")
        click.echo()

    user_document = _load_user_document(input_file, verbose)

    try:
        agent = DeepSearchAgent()

        ppt_context = {
            'output_type': 'ppt',  # PPT
            'ppt_config': {
                'style': style,
                'slides': slides,
                'depth': depth,
                'theme': theme,
                'speech_notes': speech_notes  # 
            },
            **user_document
        }

        # 
        with click.progressbar(length=100, label='PPT') as bar:
            result = await agent.search(
                query=topic,
                context=ppt_context
            )
            bar.update(100)

        click.echo()

        # 
        _display_result(result, verbose, output_type='ppt', output_format='html')

    except KeyboardInterrupt:
        click.echo(click.style("\n  ", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n : {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================
# 
# ============================================================

@cli.command()
@click.argument('project_id')
@click.option('--type', '-t', 'export_type',
              type=click.Choice(['pptx', 'pdf', 'docx', 'md'], case_sensitive=False),
              required=True,
              help='pptx(PPT), pdf(PDF), docx(Word), md(Markdown)')
@click.option('--output', '-o',
              type=str,
              default=None,
              help='')
@click.option('--verbose', '-v',
              is_flag=True,
              help='')
def export(project_id, export_type, output, verbose):
    """
    

    :

    \b
        SmartFin export 20251004_215421_2025 --type pptx
        SmartFin export 20251004_180344_ --type pdf -o report.pdf
        SmartFin export 20251004_123456_ --type docx -v
    """
    asyncio.run(_execute_export(project_id, export_type, output, verbose))


async def _execute_export(project_id: str, export_type: str, output_path: str, verbose: bool):
    """TODO: Add docstring."""

    click.echo(click.style("\n=== SmartFin  ===\n", fg="cyan", bold=True))

    if verbose:
        click.echo(f"ID: {project_id}")
        click.echo(f": {export_type.upper()}")
        if output_path:
            click.echo(f": {output_path}")
        click.echo()

    try:
        from src.export.export_manager import ExportManager

        export_manager = ExportManager()

        # 
        with click.progressbar(length=100, label=f'{export_type.upper()}') as bar:
            result = await export_manager.export_project(
                project_id=project_id,
                export_type=export_type,
                output_path=output_path
            )
            bar.update(100)

        click.echo()

        if result["status"] == "success":
            click.echo(click.style(" ", fg="green", bold=True) +
                      click.style("", fg="green"))
            click.echo(f"\n: {click.style(result['output_file'], fg='cyan')}")

            if result.get("file_size"):
                click.echo(f": {result['file_size']}")
        else:
            click.echo(click.style(" ", fg="red", bold=True) +
                      click.style(f": {result.get('error', '')}", fg="red"))
            sys.exit(1)

    except ImportError:
        click.echo(click.style(" ", fg="red"))
        click.echo("\n:")
        click.echo("  pip install python-pptx python-docx markdown2 weasyprint")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo(click.style("\n  ", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n : {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================
# 
# ============================================================

@cli.command()
@click.argument('project_id')
@click.argument('requirement')
@click.option('--verbose', '-v',
              is_flag=True,
              help='')
def iterate(project_id, requirement, verbose):
    """
    

    :

    \b
        SmartFin iterate 20251004_215421 "3"
        SmartFin iterate 20251004_180344 ""
        SmartFin iterate 20251004_123456 "5" -v
    """
    asyncio.run(_execute_iterate(project_id, requirement, verbose))


async def _execute_iterate(project_id: str, requirement: str, verbose: bool):
    """TODO: Add docstring."""

    click.echo(click.style("\n=== SmartFin  ===\n", fg="magenta", bold=True))

    if verbose:
        click.echo(f"ID: {project_id}")
        click.echo(f": {requirement}")
        click.echo()

    try:
        from src.agents.iteration_agent import IterationAgent

        iteration_agent = IterationAgent()

        # 
        with click.progressbar(length=100, label='') as bar:
            result = await iteration_agent.iterate_project(
                project_id=project_id,
                requirement=requirement
            )
            bar.update(100)

        click.echo()

        if result["status"] == "success":
            click.echo(click.style(" ", fg="green", bold=True) +
                      click.style("", fg="green"))

            click.echo(f"\n: {result.get('project_type', '')}")
            click.echo(f": {result.get('modification_scope', '')}")
            click.echo(f": {click.style(result.get('new_version', ''), fg='cyan')}")

            if result.get('output_file'):
                click.echo(f"\n: {click.style(result['output_file'], fg='cyan')}")

            if result.get('changes'):
                click.echo(f"\n:")
                for change in result['changes']:
                    click.echo(f"   {change}")
        else:
            click.echo(click.style(" ", fg="red", bold=True) +
                      click.style(f": {result.get('error', '')}", fg="red"))
            sys.exit(1)

    except ImportError:
        click.echo(click.style(" ", fg="red"))
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo(click.style("\n  ", fg="yellow"))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n : {e}", fg="red"))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================
# 
# ============================================================

@cli.command()
@click.argument('question')
@click.option('--model', '-m',
              type=click.Choice(['fast', 'balanced', 'quality'], case_sensitive=False),
              default='balanced',
              help='fast(), balanced(), quality()')
@click.option('--verbose', '-v',
              is_flag=True,
              help='')
def ask(question, model, verbose):
    """
    

    :

    \b
        SmartFin ask ""
        SmartFin ask "Python" --model quality -v
    """
    click.echo(click.style("\n=== SmartFin  ===\n", fg="blue", bold=True))
    click.echo(f": {question}\n")

    # TODO: 
    click.echo(click.style("  ...\n", fg="yellow"))


# ============================================================
# 
# ============================================================

@cli.command()
def status():
    """
    

    LLM
    """
    click.echo(click.style("\n=== SmartFin  ===\n", fg="cyan", bold=True))

    try:
        agent = DeepSearchAgent()
        status_info = agent.get_status()

        click.echo(f": {status_info.get('system', 'Unknown')}")
        click.echo(f": {click.style(' ', fg='green')}")

        if status_info.get('llm_manager'):
            llm_info = status_info['llm_manager']
            click.echo(f"\nLLM: {llm_info.get('total_configs', 0)} ")

            providers = llm_info.get('available_providers', {})
            click.echo("\n:")
            for name, info in providers.items():
                status = info.get('status', '')
                color = 'green' if status == '' else 'yellow'
                click.echo(f"   {name}: {click.style(status, fg=color)}")

        click.echo()

    except Exception as e:
        click.echo(click.style(f" : {e}", fg="red"))
        sys.exit(1)


# ============================================================
# 
# ============================================================

def _display_result(result: dict, verbose: bool, output_type: str = 'report', output_format: str = 'md'):
    """TODO: Add docstring."""

    status = result.get('status', 'unknown')

    if status == 'success':
        click.echo(click.style(" ", fg="green", bold=True) +
                   click.style("", fg="green"))
    else:
        click.echo(click.style("  ", fg="yellow") +
                   click.style(f": {status}", fg="yellow"))

    # 
    if result.get('project_id'):
        click.echo(f"\nID: {result['project_id']}")

    if result.get('project_dir'):
        project_dir = result['project_dir']
        click.echo(f": {click.style(project_dir, fg='cyan')}")

    # 
    if verbose and result.get('messages'):
        click.echo(f"\n{click.style(':', bold=True)}")
        for msg in result['messages']:
            if msg.get('agent'):
                agent = msg.get('agent', 'Unknown')
                content = msg.get('content', '')[:60]
                click.echo(f"  {click.style('', fg='green')} {agent}: {content}...")

    # 
    if result.get('final_report') and result['final_report'].get('result'):
        final_result = result['final_report']['result']

        # PPT
        if output_type == 'ppt' and final_result.get('ppt'):
            ppt_data = final_result['ppt']
            click.echo(f"\n{click.style('=== PPT ===', fg='green', bold=True)}")

            metadata = ppt_data.get('metadata', {})
            click.echo(f"\n: {ppt_data.get('title', '')}")
            click.echo(f": {metadata.get('style', '')}")
            click.echo(f": {metadata.get('slide_count', 0)}")

            # 
            if result.get('project_dir'):
                project_dir = Path(result['project_dir'])

                html_path = project_dir / 'reports' / 'FINAL_REPORT.html'
                if html_path.exists():
                    click.echo(f"\n{click.style('', fg='green')} PPT: {click.style(str(html_path), fg='cyan')}")
                    click.echo(f"   {click.style(': PPT', fg='bright_black')}")
                    click.echo(f"   {click.style(': ', fg='bright_black')}")

        # /
        elif final_result.get('report'):
            report_data = final_result['report']

            click.echo(f"\n{click.style('===  ===', fg='cyan', bold=True)}")
            click.echo(f"\n: {report_data.get('title', '')}")
            click.echo(f": {report_data.get('word_count', 0)}")

            # 
            content = report_data.get('content', '')
            if content:
                preview = content[:500].strip()
                click.echo(f"\n{preview}...")

            # 
            if result.get('project_dir'):
                project_dir = Path(result['project_dir'])

                # Markdown
                md_path = project_dir / 'reports' / 'FINAL_REPORT.md'
                click.echo(f"\n{click.style('', fg='green')} : {click.style(str(md_path), fg='cyan')}")

                # HTMLHTML
                if output_format == 'html':
                    html_path = project_dir / 'reports' / 'FINAL_REPORT.html'
                    if html_path.exists():
                        click.echo(f"{click.style('', fg='green')} HTML: {click.style(str(html_path), fg='cyan')}")
                        click.echo(f"   {click.style(': HTML', fg='bright_black')}")

    # 金融数据分析结果（report / none / ppt 均会执行分析）
    if output_type in ('financial_analysis', 'ppt'):
        data = result.get('data_analysis_results') or {}
        if data:
            click.echo(f"\n{click.style('=== 金融数据分析 ===', fg='yellow', bold=True)}")
            click.echo(f"状态: {data.get('status', 'unknown')}")
            click.echo(f"数据来源: {data.get('source_type', '')}")

            metrics = data.get('metrics') or {}
            if metrics:
                click.echo(f"\n{click.style('核心指标:', bold=True)}")
                for key, val in metrics.items():
                    click.echo(f"  · {key}: {val}")

            findings = data.get('key_findings') or []
            if findings:
                click.echo(f"\n{click.style('关键发现:', bold=True)}")
                for item in findings[:5]:
                    title = item.get('title', '')
                    value = item.get('value', '')
                    click.echo(f"  · {title}: {value}")

            charts = data.get('charts') or []
            if charts:
                click.echo(f"\n图表: {len(charts)} 个")

            if result.get('project_dir'):
                analysis_path = Path(result['project_dir']) / 'intermediate' / '03_data_analysis.json'
                if analysis_path.exists():
                    click.echo(
                        f"\n{click.style('✓', fg='green')} "
                        f"分析结果: {click.style(str(analysis_path), fg='cyan')}"
                    )

    # 
    if result.get('search_results'):
        count = len(result['search_results'])
        click.echo(f"\n{click.style('', fg='green')}  {count} ")

    # 
    if result.get('errors'):
        click.echo(f"\n{click.style(':', fg='yellow', bold=True)}")
        for error in result['errors']:
            click.echo(f"   {error}")

    click.echo()


# ============================================================
# 
# ============================================================

if __name__ == '__main__':
    cli()
