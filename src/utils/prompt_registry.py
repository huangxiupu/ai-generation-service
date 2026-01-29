import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.config import config

class PromptRegistry:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(config.TEMPLATE_DIR),
            autoescape=False
        )
        
    def render(self, template_name: str, **kwargs) -> str:
        """
        使用给定的上下文渲染模板。
        template_name: 相对于 templates 目录的路径（例如 'user_prompts/mcq_text.j2'）
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            raise ValueError(f"渲染模板 {template_name} 时出错: {str(e)}")

    def get_system_prompt(self) -> str:
        return self.render("system_prompts/base.j2")

    def get_esl_system_prompt(self, **kwargs) -> str:
        """
        获取专门的 ESL 专家系统提示词。
        需要包含 meta.grade_level 的上下文（例如 context={'meta': {'grade_level': '1'}}）
        """
        return self.render("system_prompts/esl_expert.j2", **kwargs)
