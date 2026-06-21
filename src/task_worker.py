"""TODO: Add docstring."""

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Dict, Any
from loguru import logger

# 
sys.path.append(str(Path(__file__).parent.parent))

from src.task_manager import TaskManager, TaskStatus, TaskType, get_task_manager
from src.deep_search_agent import DeepSearchAgent


class TaskWorker:
    """TODO: Add docstring."""

    def __init__(self, task_manager: TaskManager = None):
        """
        

        Args:
            task_manager: 
        """
        self.task_manager = task_manager or get_task_manager()
        self.is_running = False
        logger.info("")

    async def execute_task(self, task_id: str) -> bool:
        """
        

        Args:
            task_id: ID

        Returns:
            
        """
        task_info = self.task_manager.get_task(task_id)
        if not task_info:
            logger.error(f": {task_id}")
            return False

        logger.info(f": {task_id} ({task_info.task_type.value})")

        try:
            # 
            self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)

            # 
            if task_info.task_type == TaskType.REPORT:
                result = await self._execute_report_task(task_id, task_info)
            elif task_info.task_type == TaskType.PPT:
                result = await self._execute_ppt_task(task_id, task_info)
            elif task_info.task_type == TaskType.FILE_ANALYSIS:
                result = await self._execute_file_analysis_task(task_id, task_info)
            else:
                raise ValueError(f": {task_info.task_type}")

            # 
            if result.get('success'):
                self.task_manager.complete_task(
                    task_id,
                    result=result,
                    project_id=result.get('project_id', ''),
                    output_dir=result.get('output_dir', '')
                )
                logger.info(f": {task_id}")
                return True
            else:
                self.task_manager.fail_task(task_id, result.get('error', ''))
                logger.error(f": {task_id}")
                return False

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            logger.error(f" {task_id}: {error_msg}")
            self.task_manager.fail_task(task_id, error_msg)
            return False

    async def _execute_report_task(
        self,
        task_id: str,
        task_info
    ) -> Dict[str, Any]:
        """TODO: Add docstring."""
        query = task_info.query
        context = task_info.context

        logger.info(f": {query}")

        try:
            self.task_manager.update_task_progress(task_id, 10, "初始化报告生成")

            agent = DeepSearchAgent()

            self.task_manager.update_task_progress(task_id, 30, "开始搜索与分析")

            # : DeepSearchAgent
            result = await agent.search(query, context=context)

            self.task_manager.update_task_progress(task_id, 80, "生成报告结果")

            # 
            return {
                'success': True,
                'project_id': result.get('project_id', ''),
                'output_dir': result.get('output_dir', ''),
                'output_format': context.get('output_format', 'html'),
                'files': result.get('files', []),
                'stats': result.get('stats', {})
            }

        except Exception as e:
            logger.error(f": {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _execute_ppt_task(
        self,
        task_id: str,
        task_info
    ) -> Dict[str, Any]:
        """PPT"""
        query = task_info.query
        context = task_info.context

        logger.info(f"PPT: {query}")

        try:
            self.task_manager.update_task_progress(task_id, 10, "初始化 PPT 生成")

            agent = DeepSearchAgent()

            self.task_manager.update_task_progress(task_id, 30, "正在执行搜索与内容生成，可能需要几分钟")

            try:
                result = await asyncio.wait_for(
                    agent.search(query, context=context),
                    timeout=600
                )
            except asyncio.TimeoutError:
                error_msg = "PPT 生成超时，请稍后重试。"
                logger.error(f"PPT timeout: {task_id}")
                return {
                    'success': False,
                    'error': error_msg
                }

            self.task_manager.update_task_progress(task_id, 80, "PPT 内容生成完成，正在整理结果")

            return {
                'success': True,
                'project_id': result.get('project_id', ''),
                'output_dir': result.get('output_dir', ''),
                'slides': result.get('slides', 0),
                'files': result.get('files', []),
                'stats': result.get('stats', {})
            }

        except Exception as e:
            logger.error(f"PPT: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _execute_file_analysis_task(
        self,
        task_id: str,
        task_info
    ) -> Dict[str, Any]:
        """文件数据分析"""
        query = task_info.query
        context = task_info.context

        logger.info(f"文件分析: {query}")

        try:
            self.task_manager.update_task_progress(task_id, 10, "文件分析")

            from src.agents.data_analysis.file_analyzer import FileDataAnalyzer
            from src.storage.search_storage import SearchStorage
            from pathlib import Path
            import json
            from datetime import datetime

            # 创建与报告/PPT一致的存储目录
            storage = SearchStorage()
            project_id = storage.create_project(query)

            self.task_manager.update_task_progress(task_id, 30, "分析文件")

            analyzer = FileDataAnalyzer()
            result = analyzer.analyze_file(
                query=query,
                file_name=context.get("file_name"),
                file_type=context.get("file_type"),
                file_content=context.get("file_content"),
                use_llm=context.get("use_llm", False),
            )

            self.task_manager.update_task_progress(task_id, 70, "生成报告")

            # 导入报告构建和 sanitize 工具
            from src.agents.data_analysis.file_report import build_file_analysis_html, build_file_analysis_markdown
            from src.agents.data_analysis.report_section import build_data_analysis_section
            from src.api import _sanitize

            # 转换为原生 Python 类型
            native_result = _sanitize(result)

            # 如果开启了 LLM 分析，调用 LLM 补充语义分析
            if context.get("use_llm"):
                try:
                    from src.llm.manager import LLMManager
                    llm_manager = LLMManager()
                    llm_client = llm_manager.get_client("default")

                    prompt_parts = [
                        '你是一个数据科学家，请基于下面的统计结果和数据特征，按"总体结论 / 风险点 / 建议"三个部分输出中文分析。',
                        "\n指标：",
                        json.dumps(native_result.get("metrics", {}), ensure_ascii=False),
                    ]
                    tables = native_result.get("tables", [])
                    if tables:
                        prompt_parts.append("\n表格示例：")
                        prompt_parts.append(json.dumps(tables[0], ensure_ascii=False))
                    if native_result.get("key_findings"):
                        prompt_parts.append("\n已有结论：")
                        prompt_parts.append(json.dumps(native_result.get("key_findings"), ensure_ascii=False))

                    messages = [
                        {"role": "system", "content": "你是一个数据科学家，能把统计结果转化为业务和含义解释。"},
                        {"role": "user", "content": "\n".join(prompt_parts)}
                    ]

                    resp = await llm_client.chat_completion(messages=messages, max_tokens=800)
                    llm_text = None
                    if isinstance(resp, dict):
                        if resp.get("choices") and isinstance(resp.get("choices"), list):
                            first = resp["choices"][0]
                            llm_text = first.get("message", {}).get("content") or first.get("text") or first.get("content")
                        else:
                            llm_text = resp.get("content") or resp.get("text")

                    if llm_text:
                        native_result["llm_analysis"] = llm_text
                        native_result.setdefault("key_findings", [])
                        native_result["key_findings"].insert(0, {"title": "LLM 分析", "value": llm_text, "evidence": "LLM"})
                except Exception as e:
                    logger.warning(f"文件分析 LLM 分析失败: {e}")

            # 构建报告 section（包含 charts）
            section = build_data_analysis_section(native_result, section_index=1)
            markdown = build_file_analysis_markdown(section) if section else ""
            html = build_file_analysis_html(
                section, report_title=query or context.get("file_name") or "数据分析报告"
            ) if section else ""

            # 把 section 里的 charts 和 content_html 合并到 native_result（前端 renderFileAnalysisResult 需要）
            if section:
                if section.get("charts"):
                    native_result["charts"] = section["charts"]
                if section.get("content_html"):
                    native_result["content_html"] = section["content_html"]

            self.task_manager.update_task_progress(task_id, 85, "保存结果")

            # 保存到 storage 目录（与报告/PPT一致的结构）
            output_dir = Path(storage.get_project_dir())

            # 保存 JSON 结果
            result_path = output_dir / "reports" / "analysis_result.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(native_result, f, ensure_ascii=False, indent=2)
            logger.info(f"文件分析结果已保存: {result_path}")

            # 保存 HTML 报告
            html_path = output_dir / "reports" / "FINAL_REPORT.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"HTML报告已保存: {html_path}")

            # 保存 Markdown 报告
            md_path = output_dir / "reports" / "FINAL_REPORT.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
            logger.info(f"Markdown报告已保存: {md_path}")

            # 保存元数据
            from datetime import datetime
            metadata = {
                "project_id": project_id,
                "query": query,
                "file_name": context.get("file_name"),
                "file_type": context.get("file_type"),
                "created_at": task_info.created_at,
                "completed_at": datetime.now().isoformat(),
                "status": "success"
            }
            storage.save_metadata(metadata)

            self.task_manager.update_task_progress(task_id, 100, "完成")

            return {
                'success': True,
                'project_id': project_id,
                'output_dir': str(output_dir),
                'html_path': str(html_path),
                'md_path': str(md_path),
                'result': native_result,
                'html': html,
                'markdown': markdown,
            }

        except Exception as e:
            logger.error(f"文件分析: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    async def process_pending_tasks(self, max_tasks: int = 1) -> int:
        """
        

        Args:
            max_tasks: 

        Returns:
            
        """
        pending_tasks = self.task_manager.get_pending_tasks(limit=max_tasks)

        if not pending_tasks:
            return 0

        logger.info(f" {len(pending_tasks)} ")

        processed = 0
        for task_info in pending_tasks:
            success = await self.execute_task(task_info.task_id)
            if success:
                processed += 1

        return processed

    async def run_forever(self, interval: int = 5):
        """
        

        Args:
            interval: ()
        """
        self.is_running = True
        logger.info(f" (: {interval})")

        while self.is_running:
            try:
                # 
                processed = await self.process_pending_tasks(max_tasks=1)

                if processed > 0:
                    logger.info(f" {processed} ")

                # 
                await asyncio.sleep(interval)

            except KeyboardInterrupt:
                logger.info("")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f": {e}")
                await asyncio.sleep(interval)

        logger.info("")

    def stop(self):
        """TODO: Add docstring."""
        self.is_running = False


async def main():
    """ - """
    logger.info("=" * 50)
    logger.info("SmartFin")
    logger.info("=" * 50)

    worker = TaskWorker()

    try:
        await worker.run_forever(interval=5)
    except KeyboardInterrupt:
        logger.info("")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
