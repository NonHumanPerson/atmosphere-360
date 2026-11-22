"""
Officer Module for Atmosphere360
Command Center and CivicPulse for municipal officers.
"""
from src.officer.civic_pulse import (
    render_civic_pulse_tab,
    render_officer_complaint_queue,
)
from src.officer.command_center import (
    render_command_center_tab,
    render_inspection_route_planner,
)

__all__ = [
    "render_civic_pulse_tab",
    "render_officer_complaint_queue",
    "render_command_center_tab",
    "render_inspection_route_planner",
]