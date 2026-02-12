from .dialect import Dialect as BaseDialect
from .dialect import IN_Op
from .query_params import QueryParams


class Dialect(BaseDialect):
    def IN(self, op: IN_Op, params: QueryParams) -> str:
        if not op.value:
            return self.FALSE
        f = self.safe_str(op.field, params)
        return f'{f} = ANY({params.compile(op.value)})'
