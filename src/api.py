"""REST API - """

import json
import zipfile
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from loguru import logger

from .config import DeepSearchConfig
from .pipeline import DeepSearchPipeline
from .models import SearchResult
from .task_manager import get_task_manager, TaskType, TaskStatus


# Pydantic
class ReportRequest(BaseModel):
    """TODO: Add docstring."""
    query: str = Field(..., description="")
    report_type: str = Field("comprehensive", description=": comprehensive/daily/analysis/research")
    search_depth: str = Field("deep", description=": surface/medium/deep")
    max_results: int = Field(20, description="")
    output_format: str = Field("html", description=": html/md")
    html_template: str = Field("academic", description="HTML: academic/technical")
    html_theme: str = Field("light", description="HTML: light/dark")
    user_document: Optional[Dict[str, Any]] = Field(None, description="上传的上下文文档: {filename, content}")


class FictionRequest(BaseModel):
    """TODO: Add docstring."""
    query: str = Field(..., description="")
    genre: str = Field("mystery", description=": mystery/scifi/fantasy/horror/romance/wuxia")
    length: str = Field("short", description=": short/medium/long")
    viewpoint: str = Field("first", description=": first/third/omniscient")
    constraints: List[str] = Field(default_factory=list, description="")
    output_format: str = Field("html", description=": html/md")
    html_template: str = Field("novel", description="HTML")
    html_theme: str = Field("sepia", description="HTML")
    user_document: Optional[Dict[str, Any]] = Field(None, description="上传的上下文文档: {filename, content}")


class PPTRequest(BaseModel):
    """PPT"""
    query: str = Field(..., description="PPT")
    slides: int = Field(15, description="")
    style: str = Field("business", description=": business/creative/minimal/educational")
    theme: str = Field("corporate-blue", description="")
    depth: str = Field("medium", description=": surface/medium/deep")
    speech_notes: Optional[str] = Field("", description="演说稿说明")
    user_document: Optional[Dict[str, Any]] = Field(None, description="上传的上下文文档: {filename, content}")


class TaskResponse(BaseModel):
    """TODO: Add docstring."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """TODO: Add docstring."""
    task_id: str
    task_type: str
    status: str
    progress: int
    current_step: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# FastAPI
app = FastAPI(
    title="XunLong API",
    description="AIAPI - PPT",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files - mount frontend-static
import pathlib
frontend_static = pathlib.Path("frontend-static")
if frontend_static.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static)), name="frontend-static")
    logger.info(f"Frontend static files mounted at /static")

# 
task_manager = get_task_manager()

# 
config = DeepSearchConfig()
pipeline = DeepSearchPipeline(config)

# 
from .task_worker import TaskWorker

task_worker = TaskWorker(task_manager=task_manager)


@app.get("/")
async def root():
    """Serve frontend or redirect to it."""
    index_path = frontend_static / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "XunLong API",
        "version": "1.0.0",
        "description": "AIAPI",
        "features": ["", "", "PPT"],
        "endpoints": {
            "async_tasks": {
                "create_report": "POST /api/v1/tasks/report",
                "create_fiction": "POST /api/v1/tasks/fiction",
                "create_ppt": "POST /api/v1/tasks/ppt",
                "get_status": "GET /api/v1/tasks/{task_id}",
                "get_result": "GET /api/v1/tasks/{task_id}/result",
                "download_file": "GET /api/v1/tasks/{task_id}/download",
                "cancel_task": "DELETE /api/v1/tasks/{task_id}",
                "list_tasks": "GET /api/v1/tasks"
            },
            "legacy": {
                "search": "GET /search"
            }
        }
    }


@app.get("/health")
async def health_check():
    """TODO: Add docstring."""
    return {
        "status": "healthy",
        "task_manager": "ok",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_background_worker():
    import asyncio

    asyncio.create_task(task_worker.run_forever(interval=3))


@app.on_event("startup")
async def startup_diagnostics():
    import asyncio
    from src.llm.manager import LLMManager
    from src.monitoring.langfuse_monitor import monitor

    try:
        llm_manager = LLMManager()
        default_config = llm_manager.get_config("default")
        default_client = llm_manager.get_client("default")
        probe = await default_client.chat_completion(
            messages=[{"role": "user", "content": "OK"}],
            max_tokens=1,
        )
        logger.info(
            "diagnostics: default_provider={}, default_model={}, base_url={}, probe={}",
            default_config.provider.value,
            default_config.model_name,
            default_config.base_url,
            probe.get("status", "ok"),
        )
    except Exception as exc:
        logger.error("diagnostics: default_provider_failed: {}", exc)

    try:
        available = LLMManager().get_available_providers()
        logger.info("diagnostics: available_providers={}", available)
    except Exception as exc:
        logger.error("diagnostics: available_providers_failed: {}", exc)

    logger.info(
        "diagnostics: langfuse_enabled={}",
        getattr(monitor, "enabled", False),
    )


# ============================================================
# API
# ============================================================

# Data analysis API
class DataAnalysisRequest(BaseModel):
    query: str = Field(...)
    search_results: Optional[List[Dict[str, Any]]] = Field(None)
    rag_pack: Optional[Dict[str, Any]] = Field(None)
    use_mock: bool = Field(False)


@app.post("/api/v1/data_analysis/charts")
async def data_analysis_charts(request: DataAnalysisRequest):
    """返回 ECharts option 列表及结构化分析结果。"""
    try:
        from src.agents.data_analysis.rag_client import RAGClient
        from src.agents.data_analysis.evidence_adapter import parse_rag_evidence_pack, build_analysis_input
        from src.agents.data_analysis.financial_analyzer import FinancialAnalyzer
        from src.agents.data_analysis.chart_builder import build_charts
        from src.agents.data_analysis.report_section import build_data_analysis_section

        query = request.query
        search_results = request.search_results or []
        rag_pack_raw = request.rag_pack
        use_mock = request.use_mock

        # parse rag pack if provided
        rag_refs = []
        if rag_pack_raw and isinstance(rag_pack_raw, dict):
            rag_pack = parse_rag_evidence_pack(rag_pack_raw)
            # convert to simple RAGReference list for analyzer
            from src.agents.data_analysis.evidence_adapter import rag_pack_to_refs
            rag_refs = rag_pack_to_refs(rag_pack)
        else:
            # try to retrieve using RAGClient (may be mock)
            client = RAGClient()
            rag_refs = await client.retrieve(query)

        analyzer = FinancialAnalyzer()
        analysis_output = await analyzer.analyze(
            query=query,
            search_results=search_results,
            rag_refs=rag_refs,
            use_mock=use_mock,
            llm_callback=None,
            use_llm=False,
        )

        charts = build_charts(analysis_output)

        # assemble DataAnalysisResult-like dict
        result = {
            "status": "success",
            "source_type": "web_rag" if search_results else "mock",
            "metrics": analysis_output.metrics,
            "tables": [t.model_dump() for t in analysis_output.tables],
            "charts": charts,
            "key_findings": [f.model_dump() for f in analysis_output.key_findings],
            "methodology": analysis_output.methodology,
            "rag_refs": [r.model_dump() for r in analysis_output.rag_refs],
            "search_refs": [r.model_dump() for r in analysis_output.search_refs],
        }

        # build report section for embedding
        da_section = build_data_analysis_section(result, section_index=999)

        return JSONResponse({"result": result, "charts": charts, "section": da_section})

    except Exception as e:
        logger.error(f"data_analysis_charts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/report", response_model=TaskResponse)
async def create_report_task(request: ReportRequest):
    """
    

    IDID
    """
    try:
        # 
        context = {
            'output_type': 'report',
            'report_type': request.report_type,
            'search_depth': request.search_depth,
            'max_results': request.max_results,
            'output_format': request.output_format,
            'html_template': request.html_template,
            'html_theme': request.html_theme,
            'user_document': request.user_document
        }

        # 
        task_id = task_manager.create_task(
            task_type=TaskType.REPORT,
            query=request.query,
            context=context
        )

        logger.info(f": {task_id}")

        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"ID: {task_id}"
        )

    except Exception as e:
        logger.error(f": {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/fiction", response_model=TaskResponse)
async def create_fiction_task(request: FictionRequest):
    """
    

    IDID
    """
    try:
        # 
        context = {
            'output_type': 'fiction',
            'genre': request.genre,
            'length': request.length,
            'viewpoint': request.viewpoint,
            'constraints': request.constraints,
            'output_format': request.output_format,
            'html_template': request.html_template,
            'html_theme': request.html_theme,
            'user_document': request.user_document
        }

        # 
        task_id = task_manager.create_task(
            task_type=TaskType.FICTION,
            query=request.query,
            context=context
        )

        logger.info(f": {task_id}")

        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"ID: {task_id}"
        )

    except Exception as e:
        logger.error(f": {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/ppt", response_model=TaskResponse)
async def create_ppt_task(request: PPTRequest):
    """
    PPT

    IDID
    """
    try:
        # 构建 context
        context = {
            'output_type': 'ppt',
            'ppt_config': {
                'slides': request.slides,
                'style': request.style,
                'theme': request.theme,
                'depth': request.depth,
                'speech_notes': request.speech_notes,
            },
            'user_document': request.user_document
        }

        # 
        task_id = task_manager.create_task(
            task_type=TaskType.PPT,
            query=request.query,
            context=context
        )

        logger.info(f"PPT: {task_id}")

        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"PPTID: {task_id}"
        )

    except Exception as e:
        logger.error(f"PPT: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    

    
    """
    task_info = task_manager.get_task(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail=f": {task_id}")

    return TaskStatusResponse(
        task_id=task_info.task_id,
        task_type=task_info.task_type.value,
        status=task_info.status.value,
        progress=task_info.progress,
        current_step=task_info.current_step,
        created_at=task_info.created_at,
        started_at=task_info.started_at,
        completed_at=task_info.completed_at,
        result=task_info.result,
        error=task_info.error
    )


@app.get("/api/v1/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """
    

    
    """
    task_info = task_manager.get_task(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail=f": {task_id}")

    response = {
        "task_id": task_id,
        "status": task_info.status.value,
        "progress": task_info.progress,
        "current_step": task_info.current_step,
        "created_at": task_info.created_at,
        "started_at": task_info.started_at,
        "completed_at": task_info.completed_at,
        "error": task_info.error
    }

    if task_info.status == TaskStatus.COMPLETED:
        response.update({
            "result": task_info.result,
            "project_id": task_info.project_id,
            "output_dir": task_info.output_dir
        })

    return response


@app.get("/api/v1/tasks/{task_id}/download")
async def download_task_file(
    task_id: str,
    file_type: str = Query("html", description=": html/md")
):
    """

    HTMLMarkdown
    """
    task_info = task_manager.get_task(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail=f": {task_id}")

    if task_info.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="")

    output_dir = Path(task_info.output_dir)

    if file_type == "html":
        # PPT 任务返回 zip 压缩包（包含所有 slide 文件），普通报告返回单个 HTML
        if task_info.task_type == TaskType.PPT:
            ppt_dir = output_dir / "ppt"
            if not ppt_dir.exists():
                raise HTTPException(status_code=404, detail="PPT 目录不存在")
            # 打包成 zip 放到 output_dir，文件名加时间戳避免覆盖
            import time as _time
            zip_name = f"ppt_{int(_time.time())}.zip"
            zip_path = output_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in ppt_dir.rglob("*"):
                    if file_path.is_file():
                        # 保持 ppt/ 前缀，让解压后路径完整
                        arcname = file_path.relative_to(ppt_dir)
                        zf.write(file_path, arcname)
            return FileResponse(
                path=zip_path,
                media_type="application/zip",
                filename="ppt.zip",
                headers={"Content-Disposition": "attachment; filename*=UTF-8''ppt.zip"}
            )
        else:
            file_path = output_dir / "reports" / "FINAL_REPORT.html"
        media_type = "text/html; charset=utf-8"
    elif file_type == "md":
        file_path = output_dir / "reports" / "FINAL_REPORT.md"
        media_type = "text/markdown; charset=utf-8"
    else:
        raise HTTPException(status_code=400, detail=f": {file_type}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f": {file_type}")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{file_path.name}"}
    )


@app.delete("/api/v1/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    

    
    """
    success = task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=""
        )

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": ""
    }


@app.get("/api/v1/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description=""),
    task_type: Optional[str] = Query(None, description=""),
    limit: int = Query(50, ge=1, le=200, description="")
):
    """
    

    
    """
    # 
    status_filter = TaskStatus(status) if status else None
    type_filter = TaskType(task_type) if task_type else None

    tasks = task_manager.list_tasks(
        status=status_filter,
        task_type=type_filter,
        limit=limit
    )

    return {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "task_type": t.task_type.value,
                "status": t.status.value,
                "query": t.query,
                "progress": t.progress,
                "created_at": t.created_at,
                "completed_at": t.completed_at
            }
            for t in tasks
        ]
    }


# ============================================================
# 
# ============================================================


@app.get("/search", response_model=SearchResult)
async def search_endpoint(
    q: str = Query(..., description=""),
    k: int = Query(5, ge=1, le=20, description=""),
    engine: str = Query("duckduckgo", description=""),
    headless: bool = Query(True, description="")
):
    """
    
    
    Args:
        q: 
        k:  (1-20)
        engine: 
        headless: 
        
    Returns:
        JSON
    """
    try:
        logger.info(f"API: {q} (topk={k}, engine={engine})")
        
        # 
        temp_config = DeepSearchConfig(
            headless=headless,
            search_engine=engine,
            topk=k
        )
        
        # 
        temp_pipeline = DeepSearchPipeline(temp_config)
        
        # 
        result = await temp_pipeline.search(q)
        
        logger.info(f"API: {result.success_count}/{result.total_found} ")
        return result
        
    except Exception as e:
        logger.error(f"API: {e}")
        raise HTTPException(status_code=500, detail=f": {str(e)}")


@app.get("/config")
async def get_config():
    """TODO: Add docstring."""
    return {
        "headless": config.headless,
        "search_engine": config.search_engine,
        "topk": config.topk,
        "shots_dir": config.shots_dir,
        "browser_timeout": config.browser_timeout,
        "page_wait_time": config.page_wait_time
    }


# 
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """TODO: Add docstring."""
    logger.error(f"API: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f": {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)