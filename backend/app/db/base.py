import re
from enum import Enum

from sqlalchemy import JSON, MetaData
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

# JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite in tests).
JsonB = JSON().with_variant(JSONB(), "postgresql")


def sql_enum(enum_cls: type[Enum]) -> SAEnum:
    """Persist an enum by its *value* (lowercase) rather than its member name."""
    type_name = re.sub(r"(?<!^)(?=[A-Z])", "_", enum_cls.__name__).lower()
    return SAEnum(
        enum_cls,
        name=type_name,
        values_callable=lambda members: [member.value for member in members],
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
