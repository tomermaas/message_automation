"""Utilities for rendering student-facing messages.

The project stores message templates under :mod:`logic.templates` and renders
them using `Jinja2 <https://jinja.palletsprojects.com/>`_.  Historically the
function responsible for rendering a student notification was left as a
``TODO`` which caused callers to fail at runtime.

This module now exposes :func:`build_student_message` which loads the
``student_message.j2`` template and renders it with the provided context.
The template covers both ``inserted`` and ``updated`` distance records and
expects the following context keys:

``kind``
    ``"inserted"`` or ``"updated"`` – the type of change.

``student_name``
    The student's display name.

``old_gap`` / ``new_gap``
    Previous and current gap values.  ``old_gap`` may be ``None`` when an
    initial gap record is created.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape([]),
)


def build_student_message(ctx: Dict) -> str:
    """Render a message for a student using the Jinja2 template.

    Parameters
    ----------
    ctx:
        Rendering context containing the fields described in the module
        documentation.

    Returns
    -------
    str
        The rendered message text.
    """

    template = _TEMPLATE_ENV.get_template("student_message.j2")
    return template.render(**ctx)

