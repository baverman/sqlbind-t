import ast
from textwrap import dedent
from typing import Any, Dict

import pytest

from sqlbind_t.tfstring import match_module, transform_fstrings


def execute(source: str) -> Dict[str, Any]:
    new = transform_fstrings(ast.parse(source), '@')
    code = compile(new, '<string>', 'exec')
    ctx: Dict[str, Any] = {}
    exec(code, ctx, ctx)
    return ctx


def test_simple() -> None:
    ctx = execute(
        dedent(
            """\
                from sqlbind_t.tfstring import check_template as t
                def boo(name):
                    return t(f'@SELECT {name}')
            """
        )
    )

    p1, p2 = list(ctx['boo']('zoom'))
    assert p1 == 'SELECT '
    assert p2.value == 'zoom'


def test_type_check() -> None:
    ctx = execute(
        dedent(
            """\
                from sqlbind_t.tfstring import check_template as t
                def boo(name):
                    return t(f'SELECT {name}')
            """
        )
    )
    with pytest.raises(RuntimeError, match='prefixed f-string'):
        ctx['boo']('zoom')


def test_match_module_strict_segments() -> None:
    assert match_module('mod.bar.foo', 'mod.*.foo')
    assert not match_module('mod.bar.boo.foo', 'mod.*.foo')

    # trailing ** should match any remainder
    assert match_module('mod.bar.boo.foo', 'mod.**')

    assert match_module('mod.bar.foo', 'mod.**.foo')
    assert match_module('mod.bar.boo.foo', 'mod.**.foo')
    assert match_module('mod.foo', 'mod.**.foo')
    assert not match_module('mod.bar.boo', 'mod.**.foo')

    assert match_module('tests.test_sqlbind_t', 'tests.*')
    assert not match_module('tests.pkg.test_sqlbind_t', 'tests.*')

    assert match_module('mod.bar.foo', '**')
