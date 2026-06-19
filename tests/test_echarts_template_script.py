"""Verify enhanced_professional ECharts script block renders valid JSON + JS."""
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def test_echarts_script_has_no_jinja_inside_js():
    template_path = Path(__file__).parent.parent / "src/agents/html/templates/enhanced_professional.html"
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=True,
    )
    template = env.get_template(template_path.name)
    charts = [{
        "id": "chart_4_0",
        "title": "demo",
        "option": {
            "title": {"text": "demo"},
            "grid": {"containLabel": True},
            "series": [{"type": "bar", "data": [4.17, 8.1]}],
        },
    }]
    html = template.render(
        title="t",
        toc="",
        content="<p>x</p>",
        charts=charts,
        references=[],
        project_id="abc",
        theme="light",
        custom_css="",
        generated_at="now",
        generator="test",
        stats={},
        keywords=[],
        abstract="",
    )

    assert 'type="application/json"' in html
    assert "{% for" not in html

    match = re.search(r'id="echarts-configs">(.*?)</script>', html, re.S)
    assert match, "missing echarts-configs script"
    payload = json.loads(match.group(1))
    assert payload[0]["id"] == "chart_4_0"
    assert payload[0]["option"]["grid"]["containLabel"] is True

    js_block = html.split('id="echarts-configs">', 1)[1].split("</script>", 1)[1]
    assert "{%" not in js_block
    assert "configs.forEach" in js_block
