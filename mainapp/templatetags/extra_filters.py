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


# source: https://stackoverflow.com/a/32158083/333403
@register.filter
def get_obj_attr(obj, attr):
    """
    Allows to access non-string-attributes in the template
    """
    return getattr(obj, attr)


@register.filter
def get_obj_attr_chain(obj0, chained_attrs):
    """
    Allows to access childs of childs of non-string-attributes in the template

    example:
    {{myobject|get_obj_attr_chain:"attr0:attr1:attr2"}} corresponds to myobject.attr0.attr1.attr2
    """
    attr_names = chained_attrs.split(":")
    obj = obj0
    for attr in attr_names:
        obj = getattr(obj, attr)
    return obj


@register.filter(is_safe=True)
def allow_json_script(src):
    """
    This is intended to run after bleach (which fully allows `myscript`-tags)
    :param src:
    :return:
    """

    # TODO: introduce safety checks with beautiful soup
    return src.replace("myscript", "script")

