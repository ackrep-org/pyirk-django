"""
This module contains code to integrate visualization of ERK-entities into the web application.
"""

from typing import Union
from ipydex import IPS, activate_ips_on_exception


def create_visualization(db_entity, vis_options: dict) -> Union[None, str]:
    if vis_options is None:
        return None

    return f"<!-- utc_visualization_of_{db_entity.key_str} --> \n<visualization of {db_entity}>"

