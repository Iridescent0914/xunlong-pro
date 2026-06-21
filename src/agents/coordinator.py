""" - """

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MOCK_SEARCH_PATH = PROJECT_ROOT / "fixtures" / "mock_search.json"

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
    logger.info("LangGraphagent")
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    logger.warning(f"LangGraph: {e}")
    
# 
class BaseMessage:
    def __init__(self, content: str):
        self.content = content

class AIMessage(BaseMessage):
    pass

class HumanMessage(BaseMessage):
    pass

from ..llm import LLMManager, PromptManager
from ..pipeline import DeepSearchPipeline
from .base import BaseAgent
from .task_decomposer import TaskDecomposer as TaskDecomposerAgent
from .deep_searcher import DeepSearcher as DeepSearcherAgent
from .query_optimizer import QueryOptimizerAgent
from .search_analyzer import SearchAnalyzerAgent
from .content_synthesizer import ContentSynthesizerAgent
from .report_generator import ReportGenerator as ReportGeneratorAgent
from .content_evaluator import ContentEvaluator
from ..tools.time_tool import time_tool
try:
    from src.storage import SearchStorage
except ModuleNotFoundError:
    try:
        from storage import SearchStorage
    except ModuleNotFoundError:
        from ..storage import SearchStorage
from .report import ReportCoordinator
from .output_type_detector import OutputTypeDetector
from .ppt import PPTCoordinator
from .data_analysis import DataAnalysisAgent


class DeepSearchState(TypedDict):
    """TODO: Add docstring."""
    query: str
    context: Dict[str, Any]
    messages: List[Dict[str, Any]]
    current_step: str

    # 
    user_document: Optional[str]
    user_document_meta: Dict[str, Any]
    time_context: Dict[str, Any]

    # 
    output_type: str  # "report", "ppt", "financial_analysis"
    output_type_confidence: float

    # 金融数据分析（与 search_analyzer 的 analysis_results 分离）
    data_sources: Dict[str, Any]
    data_analysis_results: Dict[str, Any]
    data_analysis_status: str

    # 
    task_analysis: Dict[str, Any]
    decomposition_status: str

    #
    search_results: List[Dict[str, Any]]
    search_status: str
    total_results: int
    refined_subtasks: List[Dict[str, Any]]  # NEW: Refined content organized by subtask

    #
    analysis_results: Dict[str, Any]
    analysis_status: str

    # 
    synthesis_results: Dict[str, Any]
    synthesis_status: str

    # PPT
    ppt_config: Dict[str, Any]  # PPT
    ppt_outline: Dict[str, Any]  # PPT
    ppt_data: Dict[str, Any]  # PPT

    # 
    final_report: Dict[str, Any]
    report_status: str

    # 
    errors: List[str]

    # 
    workflow_id: str
    timestamp: str


@dataclass
class DeepSearchConfig:
    """TODO: Add docstring."""
    max_iterations: int = 10
    timeout_seconds: int = 600  # 
    enable_parallel: bool = True
    retry_attempts: int = 3
    llm_config_name: str = "default"
    search_depth: str = "deep"  # surface, medium, deep
    max_search_results: int = 20


class DeepSearchCoordinator:
    """ - """
    
    def __init__(
        self,
        config: Optional[DeepSearchConfig] = None,
        llm_manager: Optional[LLMManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        storage: Optional[SearchStorage] = None
    ):
        self.config = config or DeepSearchConfig()
        self.llm_manager = llm_manager or LLMManager()
        self.prompt_manager = prompt_manager
        self.pipeline = DeepSearchPipeline()
        self.storage = storage or SearchStorage()

        # 
        self.agents = {
            "task_decomposer": TaskDecomposerAgent(self.llm_manager, self.prompt_manager),
            "deep_searcher": DeepSearcherAgent(self.llm_manager, self.prompt_manager),
            "query_optimizer": QueryOptimizerAgent(self.llm_manager, self.prompt_manager),
            "search_analyzer": SearchAnalyzerAgent(self.llm_manager, self.prompt_manager),
            "content_synthesizer": ContentSynthesizerAgent(self.llm_manager, self.prompt_manager),
            "report_generator": ReportGeneratorAgent(self.llm_manager, self.prompt_manager),
            "content_evaluator": ContentEvaluator(self.llm_manager, self.prompt_manager),
            "data_analyzer": DataAnalysisAgent(self.llm_manager, self.prompt_manager),
        }

        #
        self.report_coordinator = ReportCoordinator(
            self.llm_manager,
            self.prompt_manager,
            max_iterations=3,
            confidence_threshold=0.7,
            enable_images=False  # Disabled - saves time and network resources
        )

        # 
        self.output_type_detector = OutputTypeDetector(self.llm_manager, self.prompt_manager)
        
        # LangGraph
        if LANGGRAPH_AVAILABLE:
            try:
                self.workflow = self._create_langgraph_workflow()
                if self.workflow:
                    logger.info("LangGraph")
                else:
                    logger.warning("LangGraph")
                    self.workflow = None
            except Exception as e:
                logger.error(f"LangGraph: {e}")
                self.workflow = None
        else:
            self.workflow = None
            logger.info("LangGraph")
        
        logger.info("")
    
    def _create_langgraph_workflow(self):
        """LangGraph"""
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph")
            return None
        
        try:
            logger.info("LangGraph...")
            
            # 
            workflow = StateGraph(DeepSearchState)

            # 
            workflow.add_node("output_type_detector", self._output_type_detector_node)
            workflow.add_node("task_decomposer", self._task_decomposer_node)
            workflow.add_node("deep_searcher", self._deep_searcher_node)
            workflow.add_node("search_analyzer", self._search_analyzer_node)
            workflow.add_node("content_synthesizer", self._content_synthesizer_node)
            workflow.add_node("report_generator", self._report_generator_node)
            workflow.add_node("ppt_generator", self._ppt_generator_node)

            # 
            workflow.set_entry_point("output_type_detector")

            #  - 
            workflow.add_conditional_edges(
                "output_type_detector",
                self._route_by_output_type,
                {
                    "report": "task_decomposer",
                    "ppt": "task_decomposer",
                    "financial_analysis": "task_decomposer",
                }
            )

            # 
            workflow.add_conditional_edges(
                "task_decomposer",
                self._route_after_task_decomposer,
                {
                    "deep_searcher": "deep_searcher"
                }
            )

            #  - 
            workflow.add_conditional_edges(
                "deep_searcher",
                self._route_after_deep_search,
                {
                    "search_analyzer": "search_analyzer"
                }
            )

            #  - PPT / 仅分析结束
            workflow.add_conditional_edges(
                "search_analyzer",
                self._route_after_search_analyzer,
                {
                    "content_synthesizer": "content_synthesizer",
                    "ppt_generator": "ppt_generator",
                    "completed": END,
                }
            )

            # 
            workflow.add_edge("content_synthesizer", "report_generator")

            # 
            workflow.add_edge("report_generator", END)
            workflow.add_edge("ppt_generator", END)

            # 
            compiled_workflow = workflow.compile()
            logger.info("LangGraph")
            
            return compiled_workflow
            
        except Exception as e:
            logger.error(f"LangGraph: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _task_decomposer_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")

            # 
            context = state.get("context", {})
            context["output_type"] = state.get("output_type", "report")

            # 
            result = await self.agents["task_decomposer"].process({
                "query": state["query"],
                "context": context
            })

            state["task_analysis"] = result.get("result", {})
            state["decomposition_status"] = result.get("status", "unknown")

            # 
            time_context = state["task_analysis"].get("time_context") if state.get("task_analysis") else None
            if time_context:
                state["time_context"] = time_context

            subtasks_count = len(state["task_analysis"].get("subtasks", []))
            state["messages"].append({
                "role": "assistant",
                "content": f":  {subtasks_count} ",
                "agent": "task_decomposer"
            })

            state["current_step"] = "deep_searcher"

        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["decomposition_status"] = "failed"

        return state
    
    @staticmethod
    def _is_financial_analysis_mode(state: DeepSearchState) -> bool:
        """检查是否为金融分析模式：单独的金融分析任务，或报告/PPT的增强分析"""
        if state.get("output_type") == "financial_analysis":
            return True
        context = state.get("context") or {}
        # 支持两种模式：
        # 1. financial_analysis 模式：output_type == "financial_analysis"
        # 2. 报告/PPT 增强模式：context.add_data_analysis == True
        return context.get("add_data_analysis") == True

    @staticmethod
    def _load_mock_search_results() -> List[Dict[str, Any]]:
        if not MOCK_SEARCH_PATH.exists():
            logger.warning(f"Mock 搜索文件不存在: {MOCK_SEARCH_PATH}")
            return []
        return json.loads(MOCK_SEARCH_PATH.read_text(encoding="utf-8"))

    async def _run_financial_data_analysis(self, state: DeepSearchState) -> None:
        """搜索完成后执行金融数据分析（search_results + RAG）。"""
        if self._is_financial_analysis_mode(state):
            await self._data_analyzer_node(state)

    async def _data_analyzer_node(self, state: DeepSearchState) -> DeepSearchState:
        """金融数据分析智能体节点（输入：search_results + RAG）。"""
        if not self._is_financial_analysis_mode(state):
            state["data_analysis_status"] = "skipped"
            return state

        try:
            logger.info("[Coordinator] 执行金融数据分析（基于搜索结果 + RAG）...")
            context = state.get("context") or {}
            result = await self.agents["data_analyzer"].process({
                "query": state.get("query", ""),
                "search_results": state.get("search_results", []),
                "task_analysis": state.get("task_analysis", {}),
                "use_mock": context.get("use_mock_search", False),
                "rag_config": context.get("rag_config", {}),
            })
            state["data_analysis_results"] = result.get("result", {})
            state["data_analysis_status"] = result.get("status", "unknown")
            state["messages"].append({
                "role": "assistant",
                "content": f"金融数据分析完成 (status={state['data_analysis_status']})",
                "agent": "data_analyzer",
            })
        except Exception as e:
            logger.error(f"金融数据分析失败: {e}")
            state["errors"].append(f"金融数据分析失败: {e}")
            state["data_analysis_status"] = "failed"

        return state

    async def _deep_searcher_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")

            context = state.get("context") or {}
            if self._is_financial_analysis_mode(state) and context.get("use_mock_search"):
                mock_results = self._load_mock_search_results()
                state["search_results"] = mock_results
                state["search_status"] = "success" if mock_results else "failed"
                state["total_results"] = len(mock_results)
                state["messages"].append({
                    "role": "assistant",
                    "content": f"使用 Mock 搜索数据: {len(mock_results)} 条",
                    "agent": "deep_searcher",
                })
                await self._data_analyzer_node(state)
                state["current_step"] = "search_analyzer"
                return state

            task_analysis = state.get("task_analysis", {})
            subtasks = task_analysis.get("subtasks", [])
            
            if not subtasks:
                # 
                subtasks = [{
                    "id": "default_search",
                    "type": "search",
                    "title": "",
                    "search_queries": [state.get("query", "")],
                    "depth_level": self.config.search_depth
                }]
            
            all_search_results = []
            user_document = state.get("user_document")
            if user_document:
                doc_meta = state.get("user_document_meta", {})
                doc_title = doc_meta.get("filename") or ""
                doc_result = {
                    "url": doc_meta.get("source_path", "user://document"),
                    "title": doc_title,
                    "snippet": user_document[:200] if len(user_document) > 200 else user_document,
                    "content": user_document[:1000] + ("..." if len(user_document) > 1000 else ""),
                    "content_length": len(user_document),
                    "search_query": state.get("query", ""),
                    "subtask_id": "user_document",
                    "subtask_title": "",
                    "extraction_time": datetime.now().isoformat(),
                    "extracted_time": datetime.now().strftime("%Y-%m-%d"),
                    "source": "user_document",
                    "rank": 0,
                    "images": [],
                    "image_count": 0,
                    "has_images": False,
                    "images_inserted": False,
                    "has_full_content": True,
                    "extraction_status": "user_document",
                    "document_meta": doc_meta
                }
                all_search_results.append(doc_result)

                state["messages"].append({
                    "role": "assistant",
                    "content": f"{doc_title}",
                    "agent": "document_loader"
                })
            
            # 
            for subtask in subtasks:
                if subtask.get("type") == "search":
                    logger.info(f": {subtask.get('title', 'Unknown')}")
                    
                    time_context = subtask.get("time_context") or state.get("time_context")

                    search_input = {
                        "query": state.get("query", ""),
                        "decomposition": {"subtasks": [subtask]},  # 
                        "context": state.get("context", {}),
                        "time_context": time_context
                    }

                    search_result = await self.agents["deep_searcher"].process(search_input)
                    logger.debug(f": status={search_result.get('status')}, keys={list(search_result.keys())}")

                    if search_result.get("status") == "success":
                        # result
                        result_data = search_result.get("result", {})
                        task_results = result_data.get("all_content", [])
                        refined_subtasks = result_data.get("refined_subtasks", [])  # NEW

                        logger.debug(f" {len(task_results)}  {len(refined_subtasks)} ")
                        if task_results:
                            first = task_results[0]
                            logger.debug(f": url={first.get('url', '')}, title={first.get('title', '')}, content_len={len(first.get('content', ''))}")

                        all_search_results.extend(task_results)

                        # NEW: Store refined subtasks separately
                        if refined_subtasks:
                            if "refined_subtasks" not in state:
                                state["refined_subtasks"] = []
                            state["refined_subtasks"].extend(refined_subtasks)

                    #
                    await asyncio.sleep(1)
            
            # 
            if len(all_search_results) > self.config.max_search_results:
                all_search_results = all_search_results[:self.config.max_search_results]
            
            state["search_results"] = all_search_results
            state["search_status"] = "success" if all_search_results else "failed"
            state["total_results"] = len(all_search_results)
            
            state["messages"].append({
                "role": "assistant",
                "content": f":  {len(all_search_results)} ",
                "agent": "deep_searcher"
            })

            # 金融数据分析：在搜索完成后，基于 search_results + RAG 执行分析
            if self._is_financial_analysis_mode(state):
                await self._data_analyzer_node(state)

            state["current_step"] = "search_analyzer"
            
        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["search_status"] = "failed"
            state["search_results"] = []
            state["total_results"] = 0
        
        return state
    
    async def _search_analyzer_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")
            
            search_results = state.get("search_results", [])
            logger.info(f": {len(search_results)}")
            if search_results:
                logger.debug(f": {search_results[0]}")
            
            result = await self.agents["search_analyzer"].process({
                "query": state["query"],
                "search_results": search_results
            })
            
            state["analysis_results"] = result.get("result", {})
            state["analysis_status"] = result.get("status", "unknown")
            
            state["messages"].append({
                "role": "assistant",
                "content": f":  {len(state.get('search_results', []))} ",
                "agent": "search_analyzer"
            })
            
            state["current_step"] = "content_synthesizer"
            
        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["analysis_status"] = "failed"
        
        return state
    
    async def _content_synthesizer_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")
            
            result = await self.agents["content_synthesizer"].process({
                "query": state["query"],
                "search_results": state.get("search_results", []),
                "analysis_results": state.get("analysis_results", {}),
                "data_analysis_results": state.get("data_analysis_results", {}),
            })
            
            state["synthesis_results"] = result.get("result", {})
            state["synthesis_status"] = result.get("status", "unknown")
            
            state["messages"].append({
                "role": "assistant",
                "content": f"",
                "agent": "content_synthesizer"
            })
            
            state["current_step"] = "report_generator"
            
        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["synthesis_status"] = "failed"
        
        return state
    
    async def _report_generator_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")

            query = state.get("query", "")
            search_results = state.get("search_results", [])
            synthesis_results = state.get("synthesis_results", {})

            # 
            task_analysis = state.get("task_analysis", {})
            report_type = task_analysis.get("report_type", "comprehensive")

            # HTML - Always generate HTML in addition to Markdown
            context = state.get("context", {})
            output_format = context.get("output_format", "html")  # Changed default to HTML
            html_config = {
                "template": context.get("html_template", "enhanced_professional"),  # Use enhanced template
                "theme": context.get("html_theme", "light")
            }

            # 
            # ID
            project_id = state.get("workflow_id")

            result = await self.report_coordinator.generate_report(
                query=query,
                search_results=search_results,
                synthesis_results=synthesis_results,
                report_type=report_type,
                output_format=output_format,
                html_config=html_config,
                project_id=project_id,  # ID
                refined_subtasks=state.get("refined_subtasks", []),  # NEW: Pass refined subtasks
                data_analysis_results=state.get("data_analysis_results", {}),
            )

            if result["status"] == "success":
                state["final_report"] = {
                    "result": result,
                    "status": "success"
                }
                state["report_status"] = "success"

                report = result.get("report", {})
                word_count = report.get("word_count", 0)
                avg_confidence = report.get("metadata", {}).get("average_confidence", 0.0)

                state["messages"].append({
                    "role": "assistant",
                    "content": f":  {word_count}  (: {avg_confidence:.2f})",
                    "agent": "report_coordinator"
                })
            else:
                # 
                logger.warning("")

                report_input = {
                    "query": query,
                    "task_analysis": task_analysis,
                    "search_results": search_results,
                    "analysis_results": state.get("analysis_results", {}),
                    "synthesis_results": synthesis_results
                }

                fallback_result = await self.agents["report_generator"].process(report_input)

                state["final_report"] = fallback_result.get("result", {})
                state["report_status"] = fallback_result.get("status", "unknown")

                state["messages"].append({
                    "role": "assistant",
                    "content": "",
                    "agent": "report_generator"
                })

            state["current_step"] = "completed"

        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["report_status"] = "failed"

        return state

    async def _output_type_detector_node(self, state: DeepSearchState) -> DeepSearchState:
        """TODO: Add docstring."""
        try:
            logger.info("...")

            query = state.get("query", "")
            context = state.get("context", {})

            # CLI / API 显式指定 output_type 或 mode
            explicit_output_type = context.get("output_type") or context.get("mode")

            if explicit_output_type:
                # 
                output_type = explicit_output_type
                confidence = 1.0  # 100%
                logger.info(f": {output_type}")

                state["output_type"] = output_type
                state["output_type_confidence"] = confidence

                state["messages"].append({
                    "role": "assistant",
                    "content": f": {output_type}",
                    "agent": "output_type_detector"
                })

                # pptPPT
                if output_type == "ppt":
                    if "ppt_config" in context:
                        ppt_config = context["ppt_config"]
                        state["ppt_config"] = ppt_config
                        logger.info(f"PPT: style={ppt_config.get('style')}, slides={ppt_config.get('slides')}")
                    else:
                        # PPT
                        state["ppt_config"] = {
                            "style": "business",
                            "slides": 10,
                            "depth": "medium",
                            "theme": "default"
                        }
                        logger.info(f"PPT")

                elif output_type == "financial_analysis":
                    deliverable = str(context.get("deliverable") or "report").lower()
                    if deliverable == "ppt":
                        ppt_config = context.get("ppt_config") or {}
                        state["ppt_config"] = {
                            "style": ppt_config.get("style", "business"),
                            "slides": ppt_config.get("slides", 10),
                            "depth": ppt_config.get("depth", context.get("search_depth", "deep")),
                            "theme": ppt_config.get("theme", "default"),
                            "speech_notes": ppt_config.get("speech_notes"),
                        }
                        logger.info(
                            f"金融分析+PPT: style={state['ppt_config']['style']}, "
                            f"slides={state['ppt_config']['slides']}"
                        )
                    else:
                        logger.info(f"金融分析产出: {deliverable}")

            else:
                # 
                logger.info("")

                detection_result = await self.output_type_detector.detect_output_type(query)

                output_type = detection_result.get("output_type", "report")
                confidence = detection_result.get("confidence", 0.0)

                state["output_type"] = output_type
                state["output_type_confidence"] = confidence

                logger.info(f": {output_type} (: {confidence:.2f})")

                state["messages"].append({
                    "role": "assistant",
                    "content": f": {output_type} (: {confidence:.2f})",
                    "agent": "output_type_detector"
                })

        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            state["output_type"] = "report"  # 
            state["output_type_confidence"] = 0.5

        return state

    async def _ppt_generator_node(self, state: DeepSearchState) -> DeepSearchState:
        """PPT - V3"""
        try:
            logger.info("PPT (V3)...")

            query = state.get("query", "")
            search_results = state.get("search_results", [])
            ppt_config = state.get("ppt_config", {})

            # PPT
            ppt_coordinator = PPTCoordinator(self.llm_manager, self.prompt_manager)

            # output_dir (storage)
            from pathlib import Path
            output_dir = Path(self.storage.get_project_dir())

            # V3 -
            result = await ppt_coordinator.generate_ppt_v3(
                topic=query,
                search_results=search_results,
                ppt_config=ppt_config,
                output_dir=output_dir,
                data_analysis_results=state.get("data_analysis_results"),
            )

            if result["status"] == "success":
                state["ppt_data"] = {
                    "ppt_dir": result.get("ppt_dir"),
                    "total_slides": result.get("total_slides"),
                    "slide_files": result.get("slide_files"),
                    "index_page": result.get("index_page"),
                    "presenter_page": result.get("presenter_page")
                }

                # final_report - V3
                final_report_result = {
                    "ppt_dir": result.get("ppt_dir"),
                    "index_page": result.get("index_page"),
                    "presenter_page": result.get("presenter_page"),
                    "total_slides": result.get("total_slides"),
                    "output_format": "multi_html",  #
                    "slide_files": result.get("slide_files", [])
                }

                state["final_report"] = {
                    "result": final_report_result,
                    "status": "success"
                }
                state["report_status"] = "success"

                slide_count = result.get("total_slides", 0)
                logger.info(f"PPT {slide_count}  (V3)")
                logger.info(f": {result.get('index_page')}")

                state["messages"].append({
                    "role": "assistant",
                    "content": f"PPT {slide_count}  (V3)",
                    "agent": "ppt_generator"
                })
            else:
                raise Exception(result.get("error", "PPT"))

        except Exception as e:
            logger.error(f"PPT: {e}")
            import traceback
            traceback.print_exc()
            state["errors"].append(f"PPT: {e}")
            state["report_status"] = "failed"

        return state

    def _route_by_output_type(self, state: DeepSearchState) -> str:
        """TODO: Add docstring."""
        output_type = state.get("output_type", "report")
        logger.info(f": {output_type} ")
        return output_type

    def _route_after_task_decomposer(self, state: DeepSearchState) -> str:
        """TODO: Add docstring."""
        return "deep_searcher"

    def _route_after_deep_search(self, state: DeepSearchState) -> str:
        """After deep search, continue to search analysis."""
        return "search_analyzer"

    def _financial_deliverable(self, state: DeepSearchState) -> str:
        context = state.get("context") or {}
        return str(context.get("deliverable") or "report").lower()

    def _route_after_search_analyzer(self, state: DeepSearchState) -> str:
        """搜索分析后：report 走综合+报告，ppt 走演示文稿，none 仅保留分析结果。"""
        output_type = state.get("output_type", "report")

        # PPT 独立走 PPT 生成器，不受金融分析开关影响
        if output_type == "ppt":
            logger.info("PPT")
            return "ppt_generator"

        # 仅在非 PPT 时处理金融分析模式
        if self._is_financial_analysis_mode(state):
            deliverable = self._financial_deliverable(state)
            if deliverable == "ppt":
                logger.info("金融分析模式: 生成 PPT")
                return "ppt_generator"
            if deliverable == "none":
                logger.info("金融分析模式: 跳过报告/PPT")
                return "completed"
            logger.info("金融分析模式: 生成综合分析报告")
            return "content_synthesizer"

        logger.info("")
        return "content_synthesizer"

    def _route_after_synthesis(self, state: DeepSearchState) -> str:
        """TODO: Add docstring."""
        return "report_generator"

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """TODO: Add docstring."""
        try:
            context = context or {}
            if context.get("max_results") is not None:
                try:
                    self.config.max_search_results = int(context["max_results"])
                except (TypeError, ValueError):
                    logger.warning(f": max_results={context.get('max_results')}")

            if context.get("search_depth"):
                self.config.search_depth = context["search_depth"]

            # 
            project_id = self.storage.create_project(query)
            logger.info(f": {project_id}")

            # 
            workflow_id = f"deep_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Extract user_document from context (API sends {filename, content} dict)
            # Content may be plain text or "[PDF_BASE64]<base64>" for PDF uploads
            raw_user_doc = (context or {}).get("user_document")
            if isinstance(raw_user_doc, dict):
                user_doc_meta = {"filename": raw_user_doc.get("filename", "document")}
                raw_content = raw_user_doc.get("content", "")

                if isinstance(raw_content, str) and raw_content.startswith("[PDF_BASE64]"):
                    # Decode base64 PDF and extract text with pypdf
                    import base64 as _base64
                    try:
                        from pypdf import PdfReader as _PdfReader
                        from io import BytesIO as _BytesIO
                        b64_data = raw_content[len("[PDF_BASE64]"):]
                        pdf_bytes = _base64.b64decode(b64_data)
                        reader = _PdfReader(_BytesIO(pdf_bytes))
                        pdf_text_parts = []
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                pdf_text_parts.append(text)
                        user_doc_content = "\n".join(pdf_text_parts)
                        logger.info(f"PDF extracted: {len(user_doc_content)} chars from {len(reader.pages)} pages")
                        if not user_doc_content.strip():
                            logger.warning("PDF extracted text is empty, using raw PDF filename as hint")
                            user_doc_content = f"[Uploaded PDF: {user_doc_meta.get('filename', 'document')}]"
                    except Exception as e:
                        logger.error(f"PDF extraction failed: {e}, using raw content")
                        user_doc_content = f"[Uploaded PDF: {user_doc_meta.get('filename', 'document')}]"
                elif isinstance(raw_content, str):
                    user_doc_content = raw_content
                else:
                    user_doc_content = str(raw_content)
            else:
                user_doc_content = raw_user_doc
                user_doc_meta = {}

            initial_state: DeepSearchState = {
                "query": query,
                "context": context,
                "messages": [{"role": "user", "content": query}],
                "current_step": "output_type_detector",
                "user_document": user_doc_content,
                "user_document_meta": user_doc_meta,
                "time_context": (context or {}).get("time_context", {}),

                # 
                "output_type": "report",
                "output_type_confidence": 0.0,

                # 金融数据分析
                "data_sources": (context or {}).get("data_sources", {}),
                "data_analysis_results": {},
                "data_analysis_status": "pending",

                # 
                "task_analysis": {},
                "decomposition_status": "pending",

                #
                "search_results": [],
                "search_status": "pending",
                "total_results": 0,
                "refined_subtasks": [],  # NEW

                #
                "analysis_results": {},
                "analysis_status": "pending",

                # 
                "synthesis_results": {},
                "synthesis_status": "pending",

                # PPT
                "ppt_config": {},
                "ppt_outline": {},
                "ppt_data": {},

                # 
                "final_report": {},
                "report_status": "pending",

                # 
                "errors": [],

                # 
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if LANGGRAPH_AVAILABLE and self.workflow:
                # LangGraph
                logger.info("LangGraph")
                final_state = await self.workflow.ainvoke(initial_state)
            else:
                # 
                logger.info("")
                final_state = await self._simple_deep_search_workflow(initial_state)
            
            # 
            if final_state["errors"]:
                has_output = bool(final_state.get("final_report"))
                if not has_output and self._is_financial_analysis_mode(final_state):
                    da = final_state.get("data_analysis_results") or {}
                    has_output = da.get("status") in ("success", "skipped")
                status = "partial_success" if has_output else "error"
            else:
                status = "success"

            # 
            self._save_search_results(final_state, query)

            return {
                "status": status,
                "workflow_id": workflow_id,
                "query": query,
                "messages": final_state["messages"],
                "execution_steps": self._extract_execution_steps(final_state),

                # 
                "task_analysis": final_state["task_analysis"],
                "search_results": final_state["search_results"],
                "analysis_results": final_state["analysis_results"],
                "data_analysis_results": final_state.get("data_analysis_results", {}),
                "synthesis_results": final_state["synthesis_results"],
                "final_report": final_state["final_report"],

                # 
                "statistics": {
                    "total_search_results": final_state["total_results"],
                    "subtasks_count": len(final_state["task_analysis"].get("subtasks", [])),
                    "execution_time": datetime.now().isoformat(),
                    "errors_count": len(final_state["errors"])
                },

                "errors": final_state["errors"],
                "project_id": project_id,
                "project_dir": str(self.storage.get_project_dir()),
                "output_dir": str(self.storage.get_project_dir())
            }
            
        except Exception as e:
            logger.error(f": {e}")
            return {
                "status": "error",
                "workflow_id": f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "query": query,
                "error": str(e),
                "messages": [],
                "execution_steps": [],
                "task_analysis": {},
                "search_results": [],
                "analysis_results": {},
                "synthesis_results": {},
                "final_report": {},
                "statistics": {},
                "errors": [str(e)]
            }
    
    async def _simple_deep_search_workflow(self, state: DeepSearchState) -> DeepSearchState:
        """LangGraph"""
        try:
            # 1: 
            logger.info(" 1/6: ")
            state = await self._output_type_detector_node(state)

            output_type = state.get("output_type", "report")

            if output_type == "ppt":
                # PPT
                logger.info(" 2/5: 任务分解")
                state = await self._task_decomposer_node(state)

                logger.info(" 3/5: 网页搜索")
                state = await self._deep_searcher_node(state)

                logger.info(" 4/5: 内容分析")
                state = await self._search_analyzer_node(state)

                # 如果开启了 add_data_analysis，执行金融数据分析
                context = state.get("context") or {}
                if context.get("add_data_analysis"):
                    logger.info(" 4.5/6: 金融数据分析（报告增强）")
                    state = await self._data_analyzer_node(state)

                logger.info(" 5/6: 生成PPT" if context.get("add_data_analysis") else " 5/5: 生成PPT")
                state = await self._ppt_generator_node(state)

            elif output_type == "financial_analysis":
                logger.info(" 2/5: ")
                state = await self._task_decomposer_node(state)

                logger.info(" 3/5: ")
                state = await self._deep_searcher_node(state)

                logger.info(" 4/5: ")
                state = await self._search_analyzer_node(state)

                deliverable = self._financial_deliverable(state)
                if deliverable == "ppt":
                    logger.info(" 5/5: PPT")
                    state = await self._ppt_generator_node(state)
                elif deliverable == "report":
                    logger.info(" 5/6: ")
                    state = await self._content_synthesizer_node(state)
                    logger.info(" 6/6: ")
                    state = await self._report_generator_node(state)
                else:
                    logger.info(" 5/5: 跳过报告/PPT（仅保留金融数据分析）")

            else:
                # 普通报告
                logger.info(" 2/6: 任务分解")
                state = await self._task_decomposer_node(state)

                logger.info(" 3/6: 网页搜索")
                state = await self._deep_searcher_node(state)

                logger.info(" 4/6: 内容分析")
                state = await self._search_analyzer_node(state)

                # 如果开启了 add_data_analysis，执行金融数据分析
                context = state.get("context") or {}
                if context.get("add_data_analysis"):
                    logger.info(" 4.5/7: 金融数据分析（报告增强）")
                    state = await self._data_analyzer_node(state)

                logger.info(" 5/7: 内容综合" if context.get("add_data_analysis") else " 5/6: 内容综合")
                state = await self._content_synthesizer_node(state)

                logger.info(" 6/7: 生成报告" if context.get("add_data_analysis") else " 6/6: 生成报告")
                state = await self._report_generator_node(state)

            return state

        except Exception as e:
            logger.error(f": {e}")
            state["errors"].append(f": {e}")
            return state
    
    def _save_search_results(self, final_state: DeepSearchState, query: str):
        """TODO: Add docstring."""
        try:
            # 1. 
            if final_state.get("task_analysis"):
                self.storage.save_task_decomposition(final_state["task_analysis"])

            # 2.
            if final_state.get("search_results"):
                search_data = {
                    "all_content": final_state["search_results"],
                    "total_results": final_state.get("total_results", 0),
                    "search_status": final_state.get("search_status", "unknown")
                }
                self.storage.save_search_results(search_data)

            # 2b. NEW: Save refined subtasks
            if final_state.get("refined_subtasks"):
                self.storage.save_refined_subtasks(final_state["refined_subtasks"])
                logger.info(f"[Coordinator]  {len(final_state['refined_subtasks'])} ")

            # 3.
            if final_state.get("analysis_results"):
                self.storage.save_search_analysis(final_state["analysis_results"])

            # 3b. 金融数据分析结果
            if final_state.get("data_analysis_results"):
                self.storage.save_data_analysis(final_state["data_analysis_results"])

            # 4. 
            if final_state.get("synthesis_results"):
                self.storage.save_content_synthesis(final_state["synthesis_results"])

            # 5. 
            if final_state.get("final_report"):
                # 
                final_report_data = final_state["final_report"]

                #  {"result": {"report": ...}}
                if "result" in final_report_data and isinstance(final_report_data["result"], dict):
                    report_to_save = final_report_data["result"]
                else:
                    report_to_save = final_report_data

                self.storage.save_final_report(report_to_save, query)

            # 6. 
            if final_state.get("messages"):
                self.storage.save_execution_log(final_state["messages"])

            logger.info(f"[Coordinator] : {self.storage.get_project_dir()}")

        except Exception as e:
            logger.error(f"[Coordinator] : {e}")

    def _extract_execution_steps(self, final_state: DeepSearchState) -> List[str]:
        """TODO: Add docstring."""
        steps = []
        
        # 
        if final_state.get("decomposition_status") == "success":
            task_count = len(final_state.get("task_analysis", {}).get("subtasks", []))
            steps.append(f"  ({task_count} )")
        else:
            steps.append(" ")
        
        # 
        if final_state.get("search_status") == "success":
            search_count = final_state.get("total_results", 0)
            steps.append(f"  ({search_count} )")
        else:
            steps.append(" ")
        
        # 
        if final_state.get("analysis_status") == "success":
            steps.append(" ")
        else:
            steps.append(" ")
        
        # 
        if final_state.get("synthesis_status") == "success":
            steps.append(" ")
        else:
            steps.append(" ")
        
        # 
        if final_state.get("report_status") == "success":
            report = final_state.get("final_report", {}).get("report", {})
            word_count = len(report.get("content", ""))
            steps.append(f"  ({word_count} )")
        else:
            steps.append(" ")
        
        return steps
    
    async def quick_answer(self, query: str) -> str:
        """Quick answer using LLM."""
        try:
            # Try to load from YAML
            try:
                system_prompt = self.prompt_manager.get_prompt(
                    "agents/quick_answer/system",
                    default="你是一个有用的AI助手，请简洁准确地回答用户问题。"
                )
            except (KeyError, Exception):
                system_prompt = "你是一个有用的AI助手，请简洁准确地回答用户问题。"

            # LLM
            client = self.llm_manager.get_client("default")
            answer = await client.simple_chat(query, system_prompt)
            return answer

        except Exception as e:
            logger.error(f"Quick answer failed: {e}")
            return f"Error: {e}"
    
    def get_agent_status(self) -> Dict[str, Any]:
        """TODO: Add docstring."""
        return {
            "coordinator_config": {
                "max_iterations": self.config.max_iterations,
                "timeout_seconds": self.config.timeout_seconds,
                "enable_parallel": self.config.enable_parallel,
                "retry_attempts": self.config.retry_attempts,
                "search_depth": self.config.search_depth,
                "max_search_results": self.config.max_search_results
            },
            "agents": {
                name: {
                    "name": agent.name,
                    "description": getattr(agent, 'description', f"{agent.name}"),
                    "status": "active"
                }
                for name, agent in self.agents.items()
            },
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "workflow_type": "langgraph" if LANGGRAPH_AVAILABLE else "simple"
        }


# 
class AgentCoordinator(DeepSearchCoordinator):
    """TODO: Add docstring."""
    pass
