from django import template

import markdown
import mdx_math

register = template.Library()

# see https://python-markdown.github.io/reference/#extensions
md_ext = mdx_math.MathExtension(enable_dollar_delimiter=True)
md = markdown.Markdown(extensions=['extra', md_ext])


@register.filter
def render_markdown(txt):
    return md.convert(txt)

# maybe a restart of the server is neccessary after chanching this file
