import sys, os
sys.path.insert(0, 'E:/中文信息处理/agent/xunlong-pro-main')
os.chdir('E:/中文信息处理/agent/xunlong-pro-main')

from src.agents.html.document_html_agent import DocumentHTMLAgent

agent = DocumentHTMLAgent()

for theme in ['dark', 'light']:
    html = agent.convert_to_html(
        content='',
        metadata={
            'title': 'Test Report',
            'author': 'XunLong AI',
            'date': '2026-01-01',
            'sections': [{
                'level': 2, 'title': 'Test',
                'content': 'Test', 'content_html': '<p>Test content.</p>'
            }]
        },
        template='academic',
        theme=theme
    )
    lines = html.split('\n')
    print(f'=== {theme.upper()} MODE ===')
    for i, l in enumerate(lines[9:40], start=10):
        print(f'{i:3}: {l}')

    bg = 'DARK (#2c3e50)' if theme == 'dark' else 'LIGHT (#fff)'
    txt = 'LIGHT (#ecf0f1)' if theme == 'dark' else 'DARK (#333)'
    print(f'  CSS cascade: background={bg}, text={txt}')
    print()
