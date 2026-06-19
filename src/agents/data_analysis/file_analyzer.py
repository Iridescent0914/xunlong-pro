"""
File-based data analysis for CSV / text uploads.
"""

import io
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from .schemas import DataAnalysisResult, DataFinding
from ..html.echarts_generator import EChartsGenerator

import numpy as _np


def _sanitize(obj):
    if obj is None:
        return None
    if isinstance(obj, (str, bool, int, float)):
        return obj
    if isinstance(obj, (_np.integer,)):
        return int(obj)
    if isinstance(obj, (_np.floating,)):
        return float(obj)
    if isinstance(obj, _np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    try:
        if hasattr(obj, "model_dump"):
            return _sanitize(obj.model_dump())
    except Exception:
        pass
    try:
        return obj.tolist()
    except Exception:
        return obj


class FileDataAnalyzer:
    """支持用户上传 CSV / 文本的自动数据分析模块。"""

    def analyze_file(
        self,
        query: str,
        file_name: Optional[str],
        file_type: Optional[str],
        file_content: str,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        if not file_content or not file_content.strip():
            raise ValueError("file_content 不能为空")

        content_type = self._detect_file_type(file_name, file_type, file_content)
        if content_type in ("csv", "tsv"):
            return self._analyze_csv(file_name, file_content, content_type)

        return self._analyze_text(file_name, file_content)

    def _detect_file_type(
        self,
        file_name: Optional[str],
        file_type: Optional[str],
        file_content: str,
    ) -> str:
        if file_type:
            normalized = file_type.lower().strip()
            if normalized.endswith("csv"):
                return "csv"
            if normalized.endswith("tsv"):
                return "tsv"
            if "text" in normalized or normalized.endswith("txt"):
                return "text"

        if file_name:
            ext = file_name.lower().split(".")[-1]
            if ext in ("csv", "tsv", "txt", "text"):
                return ext

        if "\t" in file_content and "," not in file_content:
            return "tsv"
        if "," in file_content and "\n" in file_content:
            return "csv"

        return "text"

    def _analyze_csv(
        self,
        file_name: Optional[str],
        content: str,
        file_type: str,
    ) -> Dict[str, Any]:
        sep = "\t" if file_type == "tsv" else ","
        df = self._load_dataframe(content, sep)
        if df is None or df.empty:
            return DataAnalysisResult(
                status="error",
                source_type="csv",
                message="CSV 文件无法解析或为空",
            ).model_dump()

        df = self._normalize_dataframe(df)
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

        metrics = {
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "numeric_columns": int(len(numeric_cols)),
            "categorical_columns": int(len(categorical_cols)),
            "missing_ratio": round(float(df.isna().sum().sum()) / max(1, len(df) * len(df.columns)), 4),
        }

        methodology = (
            "自动读取 CSV 数据，提取数值与类别列，统计缺失、分布、相关性，并生成可视化推荐。"
        )

        tables = [
            self._build_column_summary_table(df, numeric_cols, categorical_cols),
            self._build_sample_rows_table(df),
        ]

        key_findings = self._build_csv_findings(df, numeric_cols, categorical_cols)
        charts = self._build_csv_charts(df, numeric_cols, categorical_cols)

        result = DataAnalysisResult(
            status="success",
            source_type="csv",
            metrics=metrics,
            tables=[table.model_dump() if hasattr(table, "model_dump") else table for table in tables],
            charts=charts,
            key_findings=key_findings,
            methodology=methodology,
        )
        return _sanitize(result.model_dump())

    def _analyze_text(
        self,
        file_name: Optional[str],
        content: str,
    ) -> Dict[str, Any]:
        text = content.strip()
        words = re.findall(r"[\w\u4e00-\u9fff]+", text, flags=re.UNICODE)
        words = [w.lower() for w in words if len(w) > 1]
        counts = Counter(words)
        top_keywords = counts.most_common(10)

        sentence_count = len(re.findall(r"[。！？!?]", text))
        paragraph_count = len([p for p in text.split("\n") if p.strip()])

        metrics = {
            "word_count": int(len(words)),
            "sentence_count": int(sentence_count),
            "paragraph_count": int(paragraph_count),
            "unique_terms": int(len(counts)),
        }

        methodology = (
            "自动分析纯文本内容，提取关键词、篇章结构与主题概览。"
        )

        tables = [
            {
                "title": "文本关键词频次",
                "columns": ["关键词", "出现次数"],
                "rows": [[term, count] for term, count in top_keywords],
            }
        ]

        findings: List[DataFinding] = []
        if top_keywords:
            findings.append(
                DataFinding(
                    title="关键词分布",
                    value=f"最常见关键词为 {top_keywords[0][0]}，出现 {top_keywords[0][1]} 次",
                    evidence="自动统计",
                )
            )
        findings.append(
            DataFinding(
                title="文本规模",
                value=f"共 {metrics['word_count']} 个词、{metrics['sentence_count']} 个句子、{metrics['paragraph_count']} 个段落",
                evidence="自动统计",
            )
        )
        if paragraph_count > 0 and sentence_count > 0:
            findings.append(
                DataFinding(
                    title="文本节奏",
                    value=f"平均每段约 {round(metrics['word_count'] / max(1, paragraph_count))} 个词", 
                    evidence="自动统计",
                )
            )

        charts = []
        if top_keywords:
            chart_data = [
                {"name": term, "value": count}
                for term, count in top_keywords
            ]
            charts.append(
                EChartsGenerator().add_bar_chart(
                    chart_id="file_text_keyword_freq",
                    title="文本关键词频次",
                    categories=[term for term, _ in top_keywords],
                    data=[count for _, count in top_keywords],
                    y_axis_name="出现次数",
                )
            )

        result = DataAnalysisResult(
            status="success",
            source_type="text",
            metrics=metrics,
            tables=tables,
            charts=charts,
            key_findings=findings,
            methodology=methodology,
        )
        return _sanitize(result.model_dump())

    def _load_dataframe(self, content: str, sep: str) -> Optional[pd.DataFrame]:
        # 支持三种输入情况：
        # 1) 正常 CSV/TSV 文本
        # 2) JSON 数组字符串（如 pandas.to_json 输出）
        # 3) 尝试不同编码回退（utf-8 -> gbk）
        s = content.strip()
        try:
            # JSON array/object -> 尝试用 read_json 解析为 DataFrame
            if s.startswith("[") or s.startswith("{"):
                try:
                    df = pd.read_json(io.StringIO(content), orient="records")
                    return df
                except Exception:
                    # fallthrough to csv parsing
                    pass

            df = pd.read_csv(io.StringIO(content), sep=sep, on_bad_lines="skip", encoding="utf-8")
            return df
        except Exception:
            try:
                return pd.read_csv(io.StringIO(content), sep=sep, on_bad_lines="skip", encoding="gbk")
            except Exception as exc:
                logger.warning(f"CSV 解析失败: {exc}")
                return None

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns=lambda c: str(c).strip())
        for col in df.columns:
            if df[col].dtype == object:
                cleaned = df[col].astype(str).str.replace(r"[\$,％%\s]", "", regex=True)
                numeric = pd.to_numeric(cleaned, errors="coerce")
                if numeric.notna().sum() >= max(1, int(len(df) * 0.5)):
                    df[col] = numeric
        return df

    def _build_column_summary_table(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
    ) -> Dict[str, Any]:
        rows = []
        for col in df.columns:
            series = df[col]
            missing = int(series.isna().sum())
            unique = int(series.nunique(dropna=True))
            row = [
                col,
                str(series.dtype),
                int(len(series)),
                missing,
                f"{round(missing / max(1, len(series)) * 100, 2)}%",
                "",
                "",
                "",
                "",
                "",
                unique,
                "",
            ]
            if col in numeric_cols:
                row[5] = self._safe_round(series.mean())
                row[6] = self._safe_round(series.median())
                row[7] = self._safe_round(series.std())
                row[8] = self._safe_round(series.min())
                row[9] = self._safe_round(series.max())
            else:
                top = series.dropna().mode()
                if not top.empty:
                    row[11] = str(top.iloc[0])
            rows.append(row)

        return {
            "title": "CSV 数据列摘要",
            "columns": [
                "列名",
                "类型",
                "记录数",
                "缺失值",
                "缺失率",
                "均值",
                "中位数",
                "标准差",
                "最小值",
                "最大值",
                "唯一值",
                "首要值",
            ],
            "rows": rows,
        }

    def _build_correlation_table(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        corr = df[numeric_cols].corr().fillna(0)
        rows = []
        for col in numeric_cols:
            row = [col] + [self._safe_round(corr.loc[col, other]) for other in numeric_cols]
            rows.append(row)
        return {
            "title": "数值列相关性矩阵",
            "columns": ["列"] + numeric_cols,
            "rows": rows,
        }

    def _build_sample_rows_table(self, df: pd.DataFrame) -> Dict[str, Any]:
        visible_cols = list(df.columns[: min(10, len(df.columns))])
        rows = [
            [self._format_cell(value) for value in row]
            for row in df[visible_cols].head(5).itertuples(index=False, name=None)
        ]
        return {
            "title": "CSV 前 5 行样本",
            "columns": visible_cols,
            "rows": rows,
        }

    def _build_csv_findings(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
    ) -> List[DataFinding]:
        findings: List[DataFinding] = []
        findings.append(
            DataFinding(
                title="数据规模",
                value=f"共 {len(df)} 行，{len(df.columns)} 列，其中 {len(numeric_cols)} 个数值列、{len(categorical_cols)} 个非数值列",
                evidence="自动统计",
            )
        )

        missing_total = int(df.isna().sum().sum())
        missing_ratio = round(float(missing_total) / max(1, len(df) * len(df.columns)), 4)
        findings.append(
            DataFinding(
                title="缺失情况",
                value=f"数据集中共有 {missing_total} 个缺失值，缺失率约 {round(missing_ratio * 100, 2)}%",
                evidence="自动统计",
            )
        )

        if numeric_cols:
            top_variance = sorted(
                numeric_cols,
                key=lambda c: float(df[c].std(skipna=True) if c in df.columns else 0.0),
                reverse=True,
            )[:2]
            findings.append(
                DataFinding(
                    title="数值列波动",
                    value=f"波动最大的列为 {top_variance[0]}，其标准差约为 {self._safe_round(df[top_variance[0]].std(skipna=True))}",
                    evidence="自动统计",
                )
            )
            if len(numeric_cols) >= 2:
                corr = df[numeric_cols].corr().abs()
                strong_pairs = []
                for i, col in enumerate(numeric_cols):
                    for j, other in enumerate(numeric_cols):
                        if i < j and corr.loc[col, other] >= 0.8:
                            strong_pairs.append((col, other, self._safe_round(corr.loc[col, other])))
                if strong_pairs:
                    pair_desc = ", ".join(
                        [f"{a}/{b}={c}" for a, b, c in strong_pairs[:3]]
                    )
                    findings.append(
                        DataFinding(
                            title="高度相关特征",
                            value=f"检测到强相关列组合：{pair_desc}",
                            evidence="自动相关性分析",
                        )
                    )

        return findings

    def _build_csv_charts(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
    ) -> List[Dict[str, Any]]:
        charts: List[Dict[str, Any]] = []
        generator = EChartsGenerator()

        # categorical distribution chart: only show when category values are informative
        if categorical_cols:
            cat_col = categorical_cols[0]
            unique_count = df[cat_col].nunique(dropna=True)
            if unique_count > 1 and unique_count <= 10:
                top_counts = df[cat_col].value_counts().head(8)
                data = [
                    {"name": str(name), "value": int(count)}
                    for name, count in top_counts.items()
                ]
                charts.append(
                    generator.add_pie_chart(
                        chart_id="file_csv_category_distribution",
                        title=f"{cat_col} 分布",
                        data=data,
                    )
                )

        # numeric summary: use dual-axis to compare均值和波动，避免量级差异导致单一柱状图失真
        if numeric_cols:
            numeric_slice = numeric_cols[: min(10, len(numeric_cols))]
            mean_values = [self._safe_round(df[col].mean(skipna=True)) for col in numeric_slice]
            std_values = [self._safe_round(df[col].std(skipna=True)) for col in numeric_slice]
            charts.append(
                generator.add_dual_axis_chart(
                    chart_id="file_csv_mean_std",
                    title="数值列均值与波动",
                    categories=[str(col) for col in numeric_slice],
                    bar_data=mean_values,
                    line_data=std_values,
                    bar_name="均值",
                    line_name="标准差",
                    bar_y_axis_name="平均值",
                    line_y_axis_name="标准差",
                )
            )

            if len(numeric_cols) >= 2:
                heatmap_data = []
                corr = df[numeric_cols].corr().fillna(0)
                for i, row in enumerate(numeric_cols):
                    for j, col in enumerate(numeric_cols):
                        heatmap_data.append([j, i, self._safe_round(corr.loc[row, col])])
                charts.append(
                    generator.add_heatmap(
                        chart_id="file_csv_correlation",
                        title="数值列相关性",
                        x_categories=[str(c) for c in numeric_cols],
                        y_categories=[str(c) for c in numeric_cols],
                        data=heatmap_data,
                    )
                )

        return charts

    def _safe_round(self, value: Any) -> Any:
        try:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return ""
            if isinstance(value, float):
                return round(value, 3)
            return value
        except Exception:
            return value

    def _format_cell(self, value: Any) -> Any:
        if pd.isna(value):
            return ""
        return value
