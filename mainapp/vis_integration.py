"""
This module contains code to integrate visualization of ERK-entities into the web application.
"""

from typing import Union

from django.urls import reverse
from ipydex import IPS, activate_ips_on_exception

from pyerk import visualization


def create_visualization(db_entity, vis_options: dict) -> Union[None, str]:
    if vis_options is None:
        return None

    url_template = reverse("entityvisualization", kwargs=dict(key_str="__xxx__")).replace("__xxx__", "{short_key}")
    svg_data = visualization.visualize_entity(db_entity.short_key, return_svg_data=True, url_template=url_template)

    return f"<!-- utc_visualization_of_{db_entity.short_key} --> \n{svg_data.decode('utf8')}"
