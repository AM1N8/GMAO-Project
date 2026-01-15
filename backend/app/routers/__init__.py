"""
Routers package - API endpoint definitions.
"""

from app.routers import (
    equipment,
    interventions,
    spare_parts,
    technicians,
    kpi,
    import_export,
    rag,
    chat,
    ocr,
    amdec,
    training,
    copilot
)

__all__ = [
    "equipment",
    "interventions",
    "spare_parts",
    "technicians",
    "kpi",
    "import_export",
    "rag",
    "chat",
    "ocr",
    "amdec",
    "training",
    "copilot"
]