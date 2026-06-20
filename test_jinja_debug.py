from jinja2 import Environment, FileSystemLoader, nodes
from datetime import datetime
import dis

def dateformat_filter(value, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

env = Environment(
    loader=FileSystemLoader(['E:/中文信息处理/agent/xunlong-pro-main/templates/html/document']),
    autoescape=True,
    trim_blocks=True
)
env.filters['dateformat'] = dateformat_filter

src, _, _ = env.loader.get_source(env, 'academic.html')

# Compile to get code objects
code = env.compile(src, 'academic.html')

# The code object for the root block (first const is the root function)
root_code = code.co_consts[3]
print(f"Root function code object: {root_code}")
print(f"Root code consts: {root_code.co_consts[:10]}")
print()

# Disassemble the root function to see the bytecode
print("=== DISASSEMBLY OF ROOT FUNCTION ===")
dis.dis(root_code)
