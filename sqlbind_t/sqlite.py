from typing import Union

from .compat import Collection
from .dialect import Dialect as BaseDialect
from .dialect import IN_Op
from .query_params import QueryParams


class Dialect(BaseDialect):
    """SQLite-specific dialect.

    Uses expanded markers for short `IN` lists and literal expansion for long
    lists to avoid SQLite parameter limit issues.
    """

    FALSE = '0'
    IN_MAX_VALUES = 10

    def IN(self, op: IN_Op, params: QueryParams) -> str:
        """Render SQLite `IN` expression."""
        values: Collection[Union[float, int, str]] = op.value  # type: ignore[assignment]
        if not values:
            return self.FALSE

        f = self.safe_str(op.field, params)
        if len(values) > self.IN_MAX_VALUES:
            # Trying to escape and assemble SQL manually to avoid too many
            # parameters exception
            return f'{f} IN ({sqlite_value_list(values)})'

        mark_list = ', '.join(params.compile(it) for it in values)
        return f'{f} IN ({mark_list})'


def sqlite_escape(val: Union[float, int, str]) -> str:
    """Escape value for literal embedding into SQLite SQL."""
    tval = type(val)
    if tval is str:
        return "'{}'".format(val.replace("'", "''"))  # type: ignore[union-attr]
    elif tval is int or tval is float:
        return str(val)
    raise ValueError(f'Invalid type: {val}')


def sqlite_value_list(values: Collection[Union[float, int, str]]) -> str:
    """Render comma-separated SQLite literal value list."""
    return ','.join(map(sqlite_escape, values))
