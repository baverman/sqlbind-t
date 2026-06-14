# sqlbind-t Reference

This document describes the supported public API exposed by `sqlbind_t`.

The package has two main layers:

- Query construction: `sqlbind_t`
- Rendering and backend integration:
   - Backend dialect: `sqlbind_t.dialect`, `sqlbind_t.sqlite`, `sqlbind_t.postgresql`
   - Parameter markers: `sqlbind_t.query_params`

## Core types

### `sqlbind_t.SQL`

Normalized composable SQL fragment. It's a thin wrapper around template strings
object

- Iterates over its string and interpolation parts
- Supports boolean-style composition operators:
  - `left & right` -> `AND(...)`
  - `left | right` -> `OR(...)`
  - `~fragment` -> `NOT ...`
- Falsey only when empty

Use `sql()` or `text()` to construct `SQL` values. Avoid calling `SQL(...)` directly unless you are extending the library at a low level.

### `sqlbind_t.EMPTY`

Empty `SQL` fragment.

Many helpers return `EMPTY` when all inputs are omitted.

### `sqlbind_t.template.Template`

Template type used by the library.

- On Python 3.14+, this is `string.templatelib.Template`
- On older Python versions, `sqlbind_t` provides a compatible implementation
- Produced implicitly by native t-strings and by the tf-string compatibility layer

Application code usually receives this type implicitly and rarely needs to instantiate it directly.

### `sqlbind_t.template.Interpolation`

Interpolation part type used inside `Template` and `SQL`.

### `sqlbind_t.UndefinedType`

Sentinel type used to mark omitted conditional values.

Most code should use the singleton `UNDEFINED` instead of constructing `UndefinedType` directly.

### `sqlbind_t.UNDEFINED`

Singleton sentinel used by conditional helpers such as `not_none`, `truthy`, `cond`, and `required`.

When a template contains an interpolation with `UNDEFINED`, that template renders as an empty fragment.

### `sqlbind_t.Expr`

Trusted identifier/expression builder.

`Expr` produces SQL text directly and does not quote or validate names.

Construction:

- `E.name` -> `name`
- `E.table.column` -> `table.column`
- `E('raw expression')` -> arbitrary trusted expression text

Supported operators and helpers:

- `expr < value`
- `expr <= value`
- `expr > value`
- `expr >= value`
- `expr == value`
- `expr != value`
- `~expr`
- `expr & other`
- `expr | other`
- `expr.IN(values)`
- `expr.LIKE(pattern, value)`
- `expr.ILIKE(pattern, value)`
- `expr.ASC`
- `expr.DESC`

Special behavior:

- `expr == None` renders `IS NULL`
- `expr != None` renders `IS NOT NULL`
- Comparing against `UNDEFINED`-producing markers yields `EMPTY`

### `sqlbind_t.E`

Shared root `Expr` instance.

Use `E` for most expression building:

```python
E.user.email
E.created_at.DESC
E('"weird table"."column"')
```

### `sqlbind_t.AnySQL`

Type alias for values accepted by most helpers and renderers.

- Equivalent to `SQL | Template`
- Use it for annotations and helper arguments that accept either a normalized `SQL` fragment or a raw template

### `sqlbind_t.SafeStr`

Type alias for values that are embedded into SQL as trusted SQL text rather than bound as parameters.

- Equivalent to `Expr | AnySQL`
- Only pass trusted identifiers or trusted SQL fragments through APIs that consume `SafeStr`

## Query construction helpers

### `sqlbind_t.text(expr: str) -> SQL`

Wraps trusted static SQL text as a `SQL` fragment.

- Interpolates nothing
- Does not quote or validate the input
- Only use with trusted SQL text

Example:

```python
text('created_at IS NOT NULL')
```

### `sqlbind_t.sql(template: AnySQL) -> SQL`

Normalizes a template-like value into `SQL`.

- Returns the same object when given `SQL`
- Returns `EMPTY` if the template contains `UNDEFINED`
- Preferred way to convert a t-string or transformed template into `SQL`

### `sqlbind_t.sqlf(template: AnySQL | str) -> SQL`

For python versions older than 3.14.

Builds `SQL` from a transformed f-string template.

- Intended for tf-string compatibility on Python versions without t-strings
- Expects a transformed string such as `sqlf(f'@SELECT ...')`
- Raises `RuntimeError` if called on an untransformed regular string

### `sqlbind_t.sqls(template: str) -> SQL`

For python versions older than 3.14.

Parses a template expression from a plain string at runtime.

- Evaluates interpolations using `eval` in the caller frame
- Useful as a last-resort compatibility fallback when t-strings are unavailable
- Less safe and less type-checker-friendly than t-strings or `sqlf`

## Clause composition

These helpers omit empty fragments automatically.

### `sqlbind_t.AND(*fragments: AnySQL) -> SQL`

Joins non-empty fragments with `AND`, wrapping the result in parentheses when needed.

### `sqlbind_t.OR(*fragments: AnySQL) -> SQL`

Joins non-empty fragments with `OR`, wrapping the result in parentheses when needed.

### `sqlbind_t.WITH(*fragments: AnySQL) -> SQL`

Builds a `WITH ...` clause from non-empty fragments.

### `sqlbind_t.WHERE(*cond: AnySQL, **kwargs: object) -> SQL`

Builds a `WHERE ...` clause.

- Positional arguments are treated as query fragments
- Keyword arguments become equality checks:
  - `value is None` -> `field IS NULL`
  - other values -> `field = ?`
  - `UNDEFINED` values are omitted
- Keyword names are embedded directly into SQL and must be trusted

### `sqlbind_t.GROUP_BY(*fields: SafeStr) -> SQL`

Builds a `GROUP BY ...` clause from trusted field expressions.

### `sqlbind_t.ORDER_BY(*fields: SafeStr) -> SQL`

Builds an `ORDER BY ...` clause from trusted field expressions.

### `sqlbind_t.SET(**kwargs: object) -> SQL`

Builds a `SET ...` clause.

- Each keyword becomes `field = value`
- `UNDEFINED` values are omitted
- Keyword names are embedded directly into SQL and must be trusted

### `sqlbind_t.VALUES(data: list[dict[str, object]] | None = None, **kwargs: object) -> SQL`

Builds a `(<columns>) VALUES (...)` fragment.

- Pass `kwargs` for a single row
- Pass `data=[...]` for multi-row inserts
- Column names are taken from the first row and embedded directly into SQL
- Row dictionaries are expected to have the same keys in the same logical order

### `sqlbind_t.AND_(template: AnySQL) -> SQL`

Prefixes a non-empty fragment with `AND `.

Useful when inlining optional filters into a larger statement.

### `sqlbind_t.OR_(template: AnySQL) -> SQL`

Prefixes a non-empty fragment with `OR `.

### `sqlbind_t.prefixed(prefix: str, template: AnySQL) -> SQL`

Low-level helper that prefixes a non-empty fragment with arbitrary trusted text.

This is part of the public module surface, but most callers should prefer the dedicated helpers above.

### `sqlbind_t.join_fragments(sep: str, flist: Sequence[SQL], wrap: tuple[str, str] | None = None, prefix: str = '') -> SQL`

Low-level helper used to join already-normalized `SQL` fragments.

Most callers should use `AND`, `OR`, `WITH`, `WHERE`, `GROUP_BY`, `ORDER_BY`, or `SET` instead.

### `sqlbind_t.assign(**kwargs: object) -> SQL`

Low-level helper that builds comma-separated `field = value` assignments without the `SET ` prefix.

Prefer `SET(...)` in application code.

## Conditional markers

These helpers work through `/` operator overloading and either return the original value or `UNDEFINED`.

### `sqlbind_t.not_none`

Omits the value when it is `None`.

Example:

```python
E.enabled == (not_none / enabled)
```

### `sqlbind_t.truthy`

Omits the value when `bool(value)` is false.

### `sqlbind_t.cond(condition)`

Factory for explicit conditional markers.

- `cond(True) / value` returns `value`
- `cond(False) / value` returns `UNDEFINED`

### `sqlbind_t.required`

Omits the wrapped value when a nested SQL fragment is empty.

Useful for wrappers like:

```python
t'WHERE {required / nested_filter}'
```

## Predicates and expression helpers

### `sqlbind_t.in_range(field: SafeStr, left: object, right: object) -> SQL`

Builds a half-open range:

```sql
field >= left AND field < right
```

- Omits the left comparison when `left is None`
- Omits the right comparison when `right is None`
- Returns `EMPTY` when both bounds are `None`

### `sqlbind_t.in_crange(field: SafeStr, left: object, right: object) -> SQL`

Builds a closed range:

```sql
field >= left AND field <= right
```

### `sqlbind_t.IN(field: SafeStr, value: Collection[object] | UndefinedType) -> SQL`

Builds a dialect-aware `IN` condition.

- `UNDEFINED` returns `EMPTY`
- Empty collections render as the dialect false expression
- Actual SQL varies by dialect:
  - generic: `field IN ?`
  - SQLite: expanded marker or literal list
  - PostgreSQL: `field = ANY(...)`

### `sqlbind_t.LIKE(field: SafeStr, template: str, value: str | UndefinedType, op: str = 'LIKE') -> SQL`

Builds a `LIKE` condition with escaping.

- Escapes `%`, `_`, and the dialect escape character in the value
- `template` is a pattern with `{}` placeholder for the escaped value
- Common templates:
  - `'{}%'` for startswith
  - `'%{}'` for endswith
  - `'%{}%'` for contains
- `UNDEFINED` returns `EMPTY`

### `sqlbind_t.ILIKE(field: SafeStr, template: str, value: str | UndefinedType) -> SQL`

Equivalent to `LIKE(..., op='ILIKE')`.

Whether `ILIKE` is valid depends on the target backend.

## Rendering API

## `sqlbind_t.dialect`

### `sqlbind_t.dialect.Dialect`

Default renderer that turns `AnySQL` into `(sql_text, params_container)`.

Important methods:

### `Dialect.render(query, params=None) -> tuple[str, QueryParams]`

Renders the query and returns:

- SQL text with backend-specific parameter markers
- The same params container instance, populated during rendering

Behavior:

- If `params` is omitted, uses `QMarkQueryParams`
- Recursively renders nested templates and `SQL` fragments
- Handles dialect operations such as `IN` and `LIKE`
- Emits identifiers from `Expr` directly

### `Dialect.safe_str(value: SafeStr, params: QueryParams) -> str`

Renders trusted SQL fragments without compiling them as bound parameters.

Useful mainly for dialect implementors.

### `Dialect.IN(op, params) -> str`

Default `IN` rendering.

- Non-empty collections render as `field IN <marker>`
- Empty collections render as `Dialect.FALSE` (`FALSE` by default)

### `Dialect.LIKE(op, params) -> str`

Default escaped `LIKE` rendering.

### `Dialect.FALSE`

Class attribute used when an operation must render a false expression.

Default value: `FALSE`

### `Dialect.LIKE_ESCAPE`

Escape character used by `LIKE`.

Default value: `\\`

### `Dialect.LIKE_CHARS`

Characters escaped by `LIKE`.

Default value: `%_`

### `sqlbind_t.dialect.render(query, params=None)`

Shortcut for `Dialect().render(...)`.

This is the most convenient renderer when the generic dialect is sufficient.

### `sqlbind_t.dialect.like_escape(value: str, escape: str = '\\', likechars: str = '%_') -> str`

Escapes a raw value for use inside a SQL `LIKE` pattern.

Prefer `LIKE` or `Expr.LIKE` when you are building a predicate, and use `like_escape` only when you need manual pattern assembly.

## Query parameter containers

## `sqlbind_t.query_params`

Each class implements a DB-API parameter marker style.

### `QueryParams`

Abstract base class with `compile(value) -> str`.

### `QMarkQueryParams`

Uses `?` markers and stores values in a list.

### `FormatQueryParams`

Uses `%s` markers and stores values in a list.

### `NumericQueryParams`

Uses `:1`, `:2`, ... markers and stores values in a list.

### `DollarQueryParams`

Uses `$1`, `$2`, ... markers and stores values in a list.

### `NamedQueryParams`

Uses `:p0`, `:p1`, ... markers and stores values in a dict.

### `PyFormatQueryParams`

Uses `%(p0)s`, `%(p1)s`, ... markers and stores values in a dict.

### `ListQueryParams`

List-backed base class for positional parameter styles.

Useful mainly for extension code.

### `DictQueryParams`

Dict-backed base class for named parameter styles.

Useful mainly for extension code.

## Backend-specific dialects

## `sqlbind_t.sqlite`

### `sqlbind_t.sqlite.Dialect`

SQLite-specific renderer.

Differences from the generic dialect:

- `FALSE` is rendered as `0`
- Short `IN` lists are expanded to `field IN (?, ?, ...)`
- Long `IN` lists are embedded as escaped SQLite literals to avoid parameter-count issues

### `Dialect.IN_MAX_VALUES`

Threshold used by SQLite `IN` rendering before switching to literal expansion.

Default value: `10`

### `sqlbind_t.sqlite.sqlite_escape(val)`

Escapes a `str`, `int`, or `float` for literal embedding into SQLite SQL.

This is a low-level helper used by the SQLite dialect.

### `sqlbind_t.sqlite.sqlite_value_list(values)`

Renders a comma-separated literal list for SQLite `IN (...)`.

This is a low-level helper used by the SQLite dialect.

## `sqlbind_t.postgresql`

### `sqlbind_t.postgresql.Dialect`

PostgreSQL-specific renderer.

Difference from the generic dialect:

- `IN` is rendered as `field = ANY(array_param)`

This is intended to work better with PostgreSQL drivers that do not support `IN %s` tuple binding directly.
