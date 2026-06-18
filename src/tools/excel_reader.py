"""Excel/CSV 读取工具（成员 1 实现）。"""

from pathlib import Path
from typing import Union


def read_tabular(path: Union[str, Path]):
    """
    读取 Excel 或 CSV，返回 pandas DataFrame。

    成员 1 TODO: 安装 pandas 后取消注释并实现。
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("请安装 pandas 和 openpyxl: pip install pandas openpyxl") from exc

    if suffix in {".csv"}:
        return pd.read_csv(file_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    raise ValueError(f"不支持的文件格式: {suffix}")
