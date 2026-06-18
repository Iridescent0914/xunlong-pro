"""
简化的工作流程测试脚本
确保完整的处理流程：读取 → 筛选 → 清洗 → 生成 Document → 切块 → 保存
"""

import sys
import os

# 确保导入正确的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("数据处理管道测试")
print("=" * 60)

# 导入必要模块
print("\n[检查] 导入必要模块...")
try:
    from process_pipeline import process_pipeline
    print("✓ 成功导入 process_pipeline")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

# 设置路径
call_parquet_path = os.path.join(os.path.dirname(__file__), 'data', 'stock_earning_call_transcripts.parquet')
news_parquet_path = os.path.join(os.path.dirname(__file__), 'data', 'stock_news.parquet')
output_dir = os.path.join(os.path.dirname(__file__), 'processed_data')

print(f"\n[配置] 文件路径:")
print(f"  电话会议: {call_parquet_path}")
print(f"  新闻: {news_parquet_path}")
print(f"  输出目录: {output_dir}")

# 检查文件是否存在
print(f"\n[检查] 源文件是否存在...")
call_exists = os.path.exists(call_parquet_path)
news_exists = os.path.exists(news_parquet_path)

print(f"  电话会议文件: {'✓ 存在' if call_exists else '✗ 不存在'}")
print(f"  新闻文件: {'✓ 存在' if news_exists else '✗ 不存在'}")

if not call_exists and not news_exists:
    print("\n⚠ 错误: 没有找到任何数据文件！")
    print("请确保以下文件存在:")
    print(f"  - {call_parquet_path}")
    print(f"  - {news_parquet_path}")
    sys.exit(1)

# 运行处理管道
print(f"\n[运行] 启动处理管道...")
try:
    docs = process_pipeline(
        call_parquet_path=call_parquet_path if call_exists else None,
        news_parquet_path=news_parquet_path if news_exists else None,
        output_dir=output_dir
    )
    print("\n✓ 处理管道执行成功！")
except Exception as e:
    print(f"\n✗ 处理管道失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("工作流程完成！")
print("=" * 60)
