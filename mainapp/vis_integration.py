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

    url_template = reverse("entityvisualization", kwargs=dict(uri="__xxx__")).replace("__xxx__", "{quoted_uri}")
    svg_data = visualization.visualize_entity(db_entity.uri, url_template=url_template)

    return f"<!-- utc_visualization_of_{db_entity.uri} --> \n{svg_data}"
