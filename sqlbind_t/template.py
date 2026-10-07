import ast
import sys
from ast import Expression, FormattedValue
from typing import Any, Generic, Iterator, List, TypeVar, Union

from .compat import pyver

_T = TypeVar('_T')

HAS_TSTRINGS = sys.version_info[:2] >= (3, 14)

TemplatePart = Union[str, 'Interpolation[Any]']

__all__ = ['Interpolation', 'Template']


class NTemplate:
    def __init__(self, *parts: TemplatePart):
        self._parts = parts

    def __iter__(self) -> Iterator[TemplatePart]:
        return iter(self._parts)

    def __bool__(self) -> bool:  # pragma: no cover
        raise RuntimeError('Raw templates should not be used as bools')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self))})'


class NInterpolation(Generic[_T]):
    def __init__(self, value: _T) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'Interpolation({self.value!r})'


if sys.version_info >= (3, 14):
    from string.templatelib import Interpolation, Template  # pragma: no cover
else:
    Template = NTemplate
    Interpolation = NInterpolation


def parse_template(string: str, *, level: int = 1) -> Template:
    root = ast.parse('f' + repr(string), mode='eval')
    frame = sys._getframe(level)
    values: List[Union[str, Interpolation[Any]]] = []
    for it in root.body.values:  # type: ignore[attr-defined]
        if type(it) is FormattedValue:
            code = compile(Expression(it.value), '<string>', 'eval')
            value = eval(code, frame.f_globals, frame.f_locals)
            values.append(Interpolation(value))
        else:
            if pyver < (3, 8):  # pragma: no cover
                values.append(it.s)
            else:
                values.append(it.value)
    return Template(*values)
