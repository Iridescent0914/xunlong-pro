你们 RAG 的输出最好不要是一段“回答”，而应该是一个**证据包 evidence pack**，方便金融数据分析 Agent 和网页搜索 Agent 的结果一起融合。

推荐标准输出格式如下：

```json
{
  "source": "financial_rag",
  "query": "分析苹果公司近期的经营风险",
  "normalized_query": "Apple recent business risks",
  "entities": {
    "company_name": "Apple Inc.",
    "ticker": "AAPL",
    "market": "US",
    "sector": "Technology"
  },
  "retrieval_scope": {
    "doc_types": ["news", "sec_filing", "earning_call"],
    "date_from": "2023-01-01",
    "date_to": "2024-12-31",
    "top_k": 8
  },
  "evidence": [
    {
      "evidence_id": "rag_AAPL_sec_filing_2024_001_chunk_03",
      "doc_id": "AAPL_10K_2024",
      "doc_type": "sec_filing",
      "title": "Apple Inc. Form 10-K 2024",
      "date": "2024-11-01",
      "source": "yahoo_finance_data",
      "url": null,
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "chunk_id": 3,
      "content": "Relevant text chunk here...",
      "summary": "该片段提到公司面临供应链、汇率和监管相关风险。",
      "score": 0.86,
      "metadata": {
        "section": "Risk Factors",
        "language": "en"
      }
    }
  ],
  "rag_summary": {
    "key_points": [
      "检索结果集中在供应链风险、监管压力和产品需求波动。",
      "SEC filing 中的风险披露比新闻更稳定，适合作为主要依据。"
    ],
    "risk_factors": [
      "供应链集中度",
      "外汇波动",
      "监管审查",
      "产品销售不确定性"
    ],
    "data_gaps": [
      "未检索到 2025 年之后的 filing 数据。"
    ]
  },
  "quality": {
    "hit_count": 8,
    "avg_score": 0.78,
    "confidence": "medium",
    "warnings": [
      "部分证据来自历史 filing，可能不是最新情况。"
    ]
  }
}
```

**最重要的字段**
你们至少要保证有这些：

```json
{
  "source": "financial_rag",
  "query": "...",
  "entities": {
    "ticker": "...",
    "company_name": "..."
  },
  "evidence": [
    {
      "doc_type": "...",
      "title": "...",
      "date": "...",
      "source": "...",
      "content": "...",
      "summary": "...",
      "score": 0.86
    }
  ],
  "rag_summary": {
    "key_points": [],
    "risk_factors": [],
    "data_gaps": []
  }
}
```

**为什么这样设计**
金融数据分析 Agent 需要的不是“RAG 帮我写一段分析”，而是：

```text
有什么证据？
证据来自哪里？
是哪家公司？
是什么时间？
相关度多高？
有没有数据缺口？
```

这样它才能和网页搜索 Agent 的结果一起比较：

```text
RAG：来自历史公告、新闻、filing、业绩会，稳定但可能不够新
网页搜索：来自实时网页，更新但噪声更大
```

然后金融数据分析 Agent 再负责统一判断。

**和网页搜索 Agent 对齐**
你们可以约定两个 Agent 都输出 `evidence` 数组，只是 `source` 不同：

```json
{
  "source": "web_search",
  "evidence": []
}
```

```json
{
  "source": "financial_rag",
  "evidence": []
}
```

这样金融数据分析 Agent 拿到后可以直接合并：

```json
{
  "query": "...",
  "rag_evidence": [],
  "web_evidence": [],
  "analysis_input": {
    "company": "...",
    "ticker": "...",
    "topic": "risk"
  }
}
```

**建议你们不要输出的东西**
RAG 这边最好不要输出：

```text
投资建议
买入/卖出结论
目标价
最终报告
未经证据支持的推断
```

这些应该交给金融数据分析 Agent 和生成 Agent。你们只负责“找证据、整理证据、说明证据质量”。

一句话：  
你们 RAG 的输出应该是**带来源、时间、公司实体、相关度和摘要的结构化证据包**，而不是最终自然语言答案。