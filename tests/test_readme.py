import pathlib
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, call

import pytest

import sqlbind_t.dialect
from sqlbind_t import AnySQL
from sqlbind_t.query_params import QMarkQueryParams
from sqlbind_t.template import HAS_TSTRINGS

from .helpers import compile_with_offset, gather_examples, norm_sql


def execute_query(query: AnySQL) -> Tuple[str, QMarkQueryParams]:
    return sqlbind_t.dialect.render(query)


def get_snippets() -> Dict[str, List[Tuple[str, str, int]]]:
    fname = 'README.md'
    text = open(pathlib.Path(__file__).parent.parent / fname).read()
    data = gather_examples(text)

    result: Dict[str, List[Tuple[str, str, int]]] = {'get_fresh_users': [], 'usage': []}

    for body, start in data:
        line = text.count('\n', 0, start) + 1
        if 'def get_fresh_users' in body:
            key = 'get_fresh_users'
        elif 'def get_user' in body:
            key = 'usage'
        else:
            print('---')
            print(body)
            print('---')
            assert False, f'Uknown README.md snippet, line {line}'
        result[key].append((fname, body, line))

    return result


snippets = get_snippets()


@pytest.mark.skipif(not HAS_TSTRINGS, reason='no t-strings')
@pytest.mark.parametrize(
    'fname,body,line',
    snippets['get_fresh_users'],
    ids=[it[2] for it in snippets['get_fresh_users']],
)
def test_get_fresh_users(fname: str, body: str, line: int) -> None:
    code = compile_with_offset(body, line - 1, fname)
    ctx: dict[str, Any] = {'execute_query': execute_query}
    exec(code, ctx)

    if 'enabled' in body:
        q, params = ctx['get_fresh_users']('date', True)
        assert params == ['date', True]
        assert (
            norm_sql(q)
            == 'SELECT * FROM users WHERE registered > ? AND enabled = ? ORDER BY registered'
        )

        q, params = ctx['get_fresh_users']('date', None)

    q, params = ctx['get_fresh_users']('date')
    assert params == ['date']
    assert norm_sql(q) == 'SELECT * FROM users WHERE registered > ? ORDER BY registered'


@pytest.mark.skipif(not HAS_TSTRINGS, reason='no t-strings')
@pytest.mark.parametrize(
    'fname,body,line',
    snippets['usage'],
    ids=[it[2] for it in snippets['usage']],
)
def test_usage(fname: str, body: str, line: int) -> None:
    code = compile_with_offset(body, line - 1, fname)
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value

    ctx: dict[str, Any] = {'connection': conn}
    exec(code, ctx)
    ctx['get_user']('some@email')

    cursor.assert_has_calls([call.execute('SELECT * FROM users WHERE email = ?', ['some@email'])])
