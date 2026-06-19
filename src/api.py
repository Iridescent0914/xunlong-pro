"""REST API - """

import json
import zipfile
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
import numpy as np


def _sanitize(obj):
    """Recursively convert numpy/pandas scalars and arrays to native Python types."""
    # primitives
    if obj is None:
        return None
    if isinstance(obj, (str, bool, int, float)):
        return obj
    # numpy scalar
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # dict
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    # list/tuple
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    # pydantic models or objects with model_dump
    try:
        if hasattr(obj, "model_dump"):
            return _sanitize(obj.model_dump())
    except Exception:
        pass
    # fallback: try to convert using iterable -> list or vars
    try:
        if hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [_sanitize(v) for v in obj]
    except Exception:
        pass
    try:
        return vars(obj)
    except Exception:
        return str(obj)
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


class FileDataAnalysisRequest(BaseModel):
    query: Optional[str] = Field("", description="分析主题或业务问题")
    file_name: Optional[str] = Field(None, description="上传文件名")
    file_type: Optional[str] = Field(None, description="文件类型提示，如 csv/text")
    file_content: str = Field(..., description="文件内容文本，CSV 或纯文本")
    output_formats: List[str] = Field(default_factory=lambda: ["json", "html", "md"], description="输出格式")
    use_llm: bool = Field(False, description="是否启用 LLM 补充分析")


@app.post("/api/v1/data_analysis/charts")
async def data_analysis_charts(request: DataAnalysisRequest):
    """返回 ECharts option 列表及结构化分析结果。"""
    try:
        from src.llm.manager import LLMManager
        from src.agents.data_analysis.data_analysis_agent import DataAnalysisAgent
        from src.agents.data_analysis.report_section import build_data_analysis_section

        query = request.query
        search_results = request.search_results or []
        use_mock = request.use_mock

        agent = DataAnalysisAgent(LLMManager())
        out = await agent.process({
            "query": query,
            "search_results": search_results,
            "use_mock": use_mock,
        })
        result = out.get("result") or {}
        charts = result.get("charts") or []

        da_section = build_data_analysis_section(result, section_index=999)

        return JSONResponse({"result": result, "charts": charts, "section": da_section})

    except Exception as e:
        logger.error(f"data_analysis_charts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/data_analysis/file")
async def data_analysis_file(request: FileDataAnalysisRequest):
    """基于用户上传的 CSV/文本生成自动数据分析报告。"""
    try:
        from src.agents.data_analysis.file_analyzer import FileDataAnalyzer
        from src.agents.data_analysis.file_report import build_file_analysis_html, build_file_analysis_markdown
        from src.agents.data_analysis.report_section import build_data_analysis_section

        analyzer = FileDataAnalyzer()
        result = analyzer.analyze_file(
            query=request.query or request.file_name or "文件分析",
            file_name=request.file_name,
            file_type=request.file_type,
            file_content=request.file_content,
            use_llm=request.use_llm,
        )

        # convert to JSON-serializable native types before further processing
        # sanitize result to native Python types (convert numpy/pandas scalars)
        try:
            native_result = _sanitize(result)
        except Exception:
            native_result = jsonable_encoder(result)

        # built-in lightweight semantic analysis (fallback when LLM not available)
        try:
            metrics = native_result.get("metrics", {})
            kfs = native_result.get("key_findings", [])
            conclusion_lines = []
            risk_lines = []
            suggestion_lines = []

            if metrics:
                rc = metrics.get("row_count")
                cc = metrics.get("column_count")
                numeric = metrics.get("numeric_columns")
                missing_ratio = metrics.get("missing_ratio")
                conclusion_lines.append(f"数据规模：约 {rc} 行、{cc} 列，其中 {numeric} 个数值列。")
                if missing_ratio and float(missing_ratio) > 0:
                    conclusion_lines.append(f"缺失情况：缺失率约 {round(float(missing_ratio) * 100, 2)}%。")
                else:
                    conclusion_lines.append("缺失情况：缺失值很少或无缺失。")
                if float(missing_ratio or 0) >= 0.05:
                    risk_lines.append("缺失率较高，可能影响分析结果准确性。")
                else:
                    suggestion_lines.append("当前数据质量较好，可继续基于现有数据进行分析和建模。 ")

            if isinstance(kfs, list) and kfs:
                for f in kfs[:3]:
                    title = f.get("title") if isinstance(f, dict) else getattr(f, "title", "")
                    value = f.get("value") if isinstance(f, dict) else getattr(f, "value", "")
                    conclusion_lines.append(f"[{title}] {value}")
                    if "相关" in str(title) or "波动" in str(title) or "缺失" in str(title):
                        risk_lines.append(f"{title} 需重点关注：{value}")

            if not risk_lines:
                risk_lines.append("目前未发现明显的风险点，但应继续关注数据的稳定性和一致性。")
            if not suggestion_lines:
                suggestion_lines.append("可从数值波动较大的列和高度相关的列入手，进一步做特征分析与风险监控。 ")

            analysis_summary = [
                "## 结构化分析",
                "### 总体结论",
                *[f"- {line}" for line in conclusion_lines],
                "",
                "### 风险点",
                *[f"- {line}" for line in risk_lines],
                "",
                "### 建议",
                *[f"- {line}" for line in suggestion_lines],
            ]
            native_result["analysis_summary"] = "\n".join(analysis_summary)
            native_result.setdefault("key_findings", [])
            native_result["key_findings"].insert(0, {"title": "自动分析摘要", "value": "\n".join(conclusion_lines[:3]), "evidence": "rule-based"})
        except Exception:
            pass

        # optionally call LLM to produce semantic interpretation
        if request.use_llm:
            try:
                from src.llm.manager import LLMManager
                llm_manager = LLMManager()
                llm_client = llm_manager.get_client("default")

                # build a concise prompt with structured sections
                prompt_parts = [
                    "你是一个数据科学家，请基于下面的统计结果和数据特征，按“总体结论 / 风险点 / 建议”三个部分输出中文分析。",
                    "\n指标：",
                    json.dumps(native_result.get("metrics", {}), ensure_ascii=False),
                ]
                # include first table and key findings
                tables = native_result.get("tables", [])
                if tables:
                    try:
                        prompt_parts.append("\n表格示例：")
                        prompt_parts.append(json.dumps(tables[0], ensure_ascii=False))
                    except Exception:
                        pass
                if native_result.get("key_findings"):
                    prompt_parts.append("\n已有结论：")
                    prompt_parts.append(json.dumps(native_result.get("key_findings"), ensure_ascii=False))

                messages = [
                    {"role": "system", "content": "你是一个数据科学家，能把统计结果转化为业务和含义解释。"},
                    {"role": "user", "content": "\n".join(prompt_parts)}
                ]

                # async call
                # call llm client (async)
                resp = await llm_client.chat_completion(messages=messages, max_tokens=800)
                # expect resp to contain 'choices' or 'content'
                llm_text = None
                if isinstance(resp, dict):
                    # try common shapes
                    if resp.get("choices") and isinstance(resp.get("choices"), list):
                        first = resp["choices"][0]
                        llm_text = first.get("message", {}).get("content") or first.get("text") or first.get("content")
                    else:
                        llm_text = resp.get("content") or resp.get("text")

                if llm_text:
                    # attach to native_result and add as a key finding so it appears in report
                    native_result["llm_analysis"] = llm_text
                    kf = {"title": "LLM 分析", "value": llm_text, "evidence": "LLM"}
                    native_result.setdefault("key_findings", [])
                    native_result["key_findings"].insert(0, kf)
            except Exception as e:
                logger.warning(f"data_analysis_file: LLM analysis failed: {e}")

        try:
            section = build_data_analysis_section(native_result, section_index=1)
            markdown = build_file_analysis_markdown(section) if section else ""
            html = build_file_analysis_html(section, report_title=request.query or request.file_name or "数据分析报告") if section else ""
        except Exception as e:
            logger.warning(f"data_analysis_file: failed to build section/report: {e}")
            section = None
            markdown = ""
            html = ""

        report: Dict[str, Any] = {}
        if "md" in [f.lower() for f in request.output_formats]:
            report["markdown"] = markdown
        if "html" in [f.lower() for f in request.output_formats]:
            report["html"] = html

        return JSONResponse(jsonable_encoder({
            "result": native_result,
            "section": section,
            "report": report,
        }))

    except Exception as e:
        logger.error(f"data_analysis_file: {e}")
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