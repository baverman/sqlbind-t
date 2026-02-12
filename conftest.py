from datetime import datetime, timedelta

import pytest

from sqlbind_t import tfstring

tfstring.init(['tests.*'], pytest=True)

import sqlbind_t.dialect
from sqlbind_t.template import HAS_TSTRINGS


def pytest_collection_modifyitems(config, items):
    if not HAS_TSTRINGS:
        marker = pytest.mark.skip(reason='no t-strings')
        for it in items:
            if it.nodeid.startswith('README.md'):
                it.add_marker(marker)


class connection:
    @staticmethod
    def execute(sql, params):
        return ['results...']


@pytest.fixture(autouse=True)
def set_doctest_ns(doctest_namespace):
    doctest_namespace['render'] = sqlbind_t.dialect.render
    doctest_namespace['connection'] = connection
    doctest_namespace['cond'] = sqlbind_t.cond
    doctest_namespace['not_none'] = sqlbind_t.not_none
    doctest_namespace['E'] = sqlbind_t.E
    doctest_namespace['datetime'] = datetime
    doctest_namespace['timedelta'] = timedelta
    doctest_namespace['AND_'] = sqlbind_t.AND_
    doctest_namespace['WHERE'] = sqlbind_t.WHERE
    doctest_namespace['sql'] = sqlbind_t.sql
    doctest_namespace['text'] = sqlbind_t.text


@pytest.fixture(autouse=True)
def set_dprint():
    calls = []

    def dprint(*args, **kwargs):
        calls.append((args, kwargs))

    __builtins__['dprint'] = dprint

    yield

    for args, kwargs in calls:
        print(*args, **kwargs)
