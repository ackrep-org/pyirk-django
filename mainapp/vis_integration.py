"""
This module contains code to integrate visualization of ERK-entities into the web application.
"""

from typing import Union
from ipydex import IPS, activate_ips_on_exception

from pyerk import visualization


def create_visualization(db_entity, vis_options: dict) -> Union[None, str]:
    if vis_options is None:
        return None

    svg_data = visualization.visualize_entity(db_entity.short_key, return_svg_data=True)

    return f"<!-- utc_visualization_of_{db_entity.short_key} --> \n{svg_data.decode('utf8')}"

