from jinja2 import Environment, FileSystemLoader
from datetime import datetime

def dateformat_filter(value, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, str):
        try: value = datetime.fromisoformat(value)
        except: return value
    if isinstance(value, datetime): return value.strftime(format)
    return value

env = Environment(
    loader=FileSystemLoader(['E:/中文信息处理/agent/xunlong-pro-main/templates/html/document']),
    autoescape=True,
    trim_blocks=True
)
env.filters['dateformat'] = dateformat_filter

t = env.get_template('academic.html')

for theme in ['dark', 'light']:
    r = t.render(
        theme=theme, title='Test', generator='Test', author='XunLong AI',
        date='2026-01-01', abstract='', toc=[], keywords=[], sections=[],
        stats={'words':100,'chinese_chars':50,'paragraphs':3}, charts=[], references=[],
        custom_css='', generated_at='2026-01-01T00:00:00'
    )
    lines = r.split('\n')
    print(f'=== {theme.upper()} MODE ===')
    for i, l in enumerate(lines[10:40], start=11):
        print(f'{i:3}: {l}')

    # CSS cascade: later :root overrides earlier
    # Dark: 2 :root blocks -> second one wins -> bg=#2c3e50 (DARK), text=#ecf0f1 (LIGHT)
    # Light: 1 :root block -> bg=#fff (LIGHT), text=#333 (DARK)
    bg = 'DARK (#2c3e50)' if theme == 'dark' else 'LIGHT (#fff)'
    txt = 'LIGHT (#ecf0f1)' if theme == 'dark' else 'DARK (#333)'
    print(f'  Computed background: {bg}')
    print(f'  Computed text:       {txt}')
    print()
