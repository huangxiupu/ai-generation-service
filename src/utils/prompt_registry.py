import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.config import config

class PromptRegistry:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(config.TEMPLATE_DIR),
            autoescape=select_autoescape(['html', 'xml', 'j2'])
        )
        
    def render(self, template_name: str, **kwargs) -> str:
        """
        Render a template with the given context.
        template_name: relative path from templates directory (e.g., 'user_prompts/mcq_text.j2')
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            raise ValueError(f"Error rendering template {template_name}: {str(e)}")

    def get_system_prompt(self) -> str:
        return self.render("system_prompts/base.j2")

    def get_esl_system_prompt(self, **kwargs) -> str:
        """
        Get the specialized ESL expert system prompt.
        Requires context with meta.grade_level (e.g. context={'meta': {'grade_level': '1'}})
        """
        return self.render("system_prompts/esl_expert.j2", **kwargs)
