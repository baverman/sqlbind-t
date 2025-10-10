import ast
import pathlib
import re
from types import CodeType
from typing import Any, List, Tuple

import pytest

import sqlbind_t.dialect
from sqlbind_t import AnySQL
from sqlbind_t.query_params import QMarkQueryParams
from sqlbind_t.template import HAS_TSTRINGS


def norm_sql(query: str) -> str:
    return re.sub(r'(?m)\s+', ' ', query.strip())


def compile_with_offset(code: str, offset: int, filename: str) -> CodeType:
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        if e.lineno:
            e.lineno += offset
            with open(filename) as f:
                e.text = f.read().splitlines()[e.lineno - 1]
        if hasattr(e, 'end_lineno'):
            e.end_lineno += offset
        raise
    ast.increment_lineno(tree, offset)
    return compile(tree, filename, 'exec')


def gather_examples(text: str, match: str) -> List[Tuple[str, int]]:
    result = []
    for it in re.finditer(r'(?sm)^```python\n(.*?)```', text):
        content = it[1]
        if match in content:
            result.append((content, it.start(1)))

    return result


def execute_query(query: AnySQL) -> Tuple[str, QMarkQueryParams]:
    return sqlbind_t.dialect.render(query)


@pytest.mark.skipif(not HAS_TSTRINGS, reason='no t-strings')
def test_readme() -> None:
    fname = 'README.md'
    text = open(pathlib.Path(__file__).parent.parent / fname).read()
    data = gather_examples(text, 'def get_fresh_users')

    for body, start in data:
        line = text.count('\n', 0, start) + 1
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
