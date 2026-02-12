from .dialect import Dialect as BaseDialect
from .dialect import IN_Op
from .query_params import QueryParams


class Dialect(BaseDialect):
    """PostgreSQL-specific dialect.

    Renders `IN` using `= ANY(array_param)`.
    """

    def IN(self, op: IN_Op, params: QueryParams) -> str:
        """Render PostgreSQL membership check via `ANY`."""
        if not op.value:
            return self.FALSE
        f = self.safe_str(op.field, params)
        return f'{f} = ANY({params.compile(op.value)})'
