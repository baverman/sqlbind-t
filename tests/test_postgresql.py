from sqlbind_t import E
from sqlbind_t.postgresql import Dialect
from sqlbind_t.query_params import DollarQueryParams

dialect = Dialect()


def test_IN() -> None:
    val = E.val
    assert dialect.render(val.IN([])) == ('FALSE', [])
    assert dialect.render(val.IN([1, 'boo'])) == ('val = ANY(?)', [[1, 'boo']])
    assert dialect.render(val.IN([1, 'boo']), DollarQueryParams()) == (
        'val = ANY($1)',
        [[1, 'boo']],
    )
