"""
HTML

MarkdownHTML
- Document
- PPT
"""

from .base_html_agent import BaseHTMLAgent, TemplateManager, get_template_manager
from .document_html_agent import DocumentHTMLAgent
from .ppt_html_agent import PPTHTMLAgent
from .template_registry import (
    TemplateRegistry,
    TemplateInfo,
    ThemeInfo,
    get_template_registry
)

__all__ = [
    'BaseHTMLAgent',
    'TemplateManager',
    'get_template_manager',
    'DocumentHTMLAgent',
    'PPTHTMLAgent',
    'TemplateRegistry',
    'TemplateInfo',
    'ThemeInfo',
    'get_template_registry',
]
