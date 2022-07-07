from django import template

import markdown
import mdx_math
from bs4 import BeautifulSoup

from ipydex import IPS, activate_ips_on_exception

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

    bs = BeautifulSoup(src, 'html.parser')
    res = bs.find_all("myscript")
    for tag in res:
        if tag.attrs.get("type") == "application/json":
            tag.name = "script"
    return str(bs)


# TODO: Obsolete?
@register.filter
def dicttype(arg: dict) -> str:
    """
    Determine some special dict structures from within the template

    :param arg:     a dict
    :return:
    """
    if len(arg) == 1:
        key, value = tuple(arg.items())[0]
        if isinstance(value, (list, tuple)):
            return "l1:list"
        else:
            return "l1"
    else:
        return "dict"


@register.filter
def foo(arg: object) -> str:
    return "foo"


@register.filter
def debug(arg: object) -> object:
    """
    start shell for debugging to examine variable content in template
    """

    IPS()
    return arg
