import ast
import re
from types import CodeType
from typing import List, Tuple

from sqlbind_t.tfstring import transform_fstrings


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
    tree = transform_fstrings(tree, '@')
    return compile(tree, filename, 'exec')


def gather_examples(text: str) -> List[Tuple[str, int]]:
    result = []
    for it in re.finditer(r'(?sm)^```python\n(.*?)```', text):
        content = it[1]
        if '>>>' not in content:
            result.append((content, it.start(1)))

    return result
