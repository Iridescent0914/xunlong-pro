import re

def clean_fin_text(raw_text: str) -> str:
    """
    金融文本通用清洗函数
    :param raw_text: 原始未清洗文本
    :return: 清洗后干净文本，空文本返回空字符串
    """
    if raw_text is None or str(raw_text).strip() == "":
        return ""

    text = str(raw_text).strip()
    # 换行、制表、回车统一替换为空格
    text = re.sub(r"[\n\t\r]+", " ", text)
    # 连续多空格压缩为单个空格
    text = re.sub(r"\s{2,}", " ", text)
    # 去除连续无意义特殊符号
    text = re.sub(r"[~#$%^&*_]{3,}", " ", text)
    text = text.strip()

    # 过滤过短无效文本
    if len(text) < 20:
        return ""
    return text