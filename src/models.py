"""Global models.

`CustomModel` is the single base every schema and table model inherits from, so
project-wide model configuration has one place to live instead of being
repeated per module.
"""

from sqlmodel import SQLModel


class CustomModel(SQLModel):
    """Base class for all schemas and table models in the project."""
