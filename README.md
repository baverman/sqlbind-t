# sqlbind-t

**sqlbind-t** allows to safely bind parameters in text based raw SQL queries using
t-string templates.

```python
>>> email = 'some@domain.com'
>>> query = t'SELECT * FROM users WHERE email = {email}'
>>> raw_sql, params = render(query)
>>> raw_sql
'SELECT * FROM users WHERE email = ?'
>>> params
['some@domain.com']
>>> connection.execute(raw_sql, params)  # your db connection instance
['results...']

```

Supports all [DBAPI parameter styles][dbapi]. Isn't limited by DBAPI compatible drivers and
could be used with anything accepting raw SQL query and parameters in some way. For example
**sqlbind-t** could be used with [SQLAlchemy textual queries][sqa-text]. Or with [clickhouse-driver][ch]'s
non-DBAPI interface.

[dbapi]: https://peps.python.org/pep-0249/#paramstyle
[sqa-text]: https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text
[ch]: https://clickhouse-driver.readthedocs.io/en/latest/quickstart.html#selecting-data


## Installation

```
pip install sqlbind-t
```


## Motivation

ORMs are great and could be used effectively for a huge number of tasks. But
after many years with SQLAlchemy I've noticed some repeating patterns:

* It's really not an easy task to decipher complex SQLAlchemy expression back into SQL.
  Especially when CTEs, sub-queries, nested queries or self-referential queries
  are involved. It composes quite well but it takes too much effort to write
  and read SQLAlchemy queries. For novices it could be a hard time to deal
  with it.

* Most of reporting queries are big enough already not to be bothered with ORMs and
  use raw SQL anyway. This kind of SQL often requires dynamic constructs and becomes
  string fiddling contraption.

* For a few tasks ORMs bring too much overhead and the only solution is to get
  down to raw DBAPI connection and raw SQL.

* (*Minor personal grudge, please ignore it*) For some ORMs (like Django ORM) your
  SQL intuition could be useless and requires deep ORM understanding.

It boils down to one thing: from time to time you have to write raw
SQL queries. I could highlight 3 types of queries:

1. Fixed queries. They don't contain any parameters. For example
   `SELECT id, name FROM users ORDER BY registered DESC LIMIT 10`.
   In general fixed queries or fixed query parts compose well and don't require any
   special treatment. Python's f-strings are enough.

2. Static queries. They contain parameters but structure is fully known beforehand.
   For example `SELECT id, name FROM users WHERE email = :email LIMIT 1`. They
   are also could be composed without large issues, especially for connection
   drivers supporting named parameters (`:param`, `%(param)s`) and accepting dicts as parameters.
   Although for positional connection drivers (`%s`, `?`) composition requires careful
   parameter tracking and queries could be fragile to change.

3. Dynamic queries. Query part presence could depend on parameter value or
   external condition. For example to provide result on input filter you have
   to add CTE and corresponding JOIN to a query. Or add filters only for non
   `None` input values. ORMs are effective for composing such queries. Using
   raw SQL are almost impossible for abstraction and leads to a complex
   boilerplate heavy code.

Note: here and in following sections I deliberately use simple examples. In real life
there is no need to use **sqlbind-t** for such kind of queries.

Note: by composing I mean ability to assemble a final query from parts which could be
abstracted and reused.

**sqlbind-t** tries to address issues with static and dynamic query types. It tracks
parameter binds and could help with dynamic query parts.


## Quick start

Some things to consider:

* **sqlbind-t** provides an API for a simple composition of raw SQL.
  On high level user operates with t-strings (Template objects) or thin wrappers
  around it. As a last step before execution user renders template into actual
  raw SQL and execution parameters.

* **sqlbind-t** doesn't parse SQL in t-strings. It only concatenates stuff
  and extracts interpolations as execution parameters.

* There is a large set of functions/methods to address dynamic queries but you
  haven't use it inline in a single query string. You could use variables to
  keep query parts and stitch resulted SQL from these parts.

* This README misses large portions of API. Feel free to explore doc strings
  with examples.

General use case looks like:

```python
import sqlbind_t.dialiect
from sqlbind_t import AnySQL

# A global alias to a dialect used by connection backend.
# There is DB specific dialect (`sqlbind_t.sqlite.Dialect` for example)
dialect = sqlbind_t.dialect.Dialect()

def execute_query(query: AnySQL):
    # Render query template into raw SQL and corresponding parameters
    raw_sql, params = dialect.render(query)
    with connection.cursor() as cursor:  # use your DBAPI connection
        return cursor.execute(raw_sql, params).fetchall()

def get_user(email: str):
    # Use t-string to capture query values
    query = t'SELECT * FROM users WHERE email = {email}'

    return execute_query(query)
```

As a shortcut you could use `sqlbind_t.dialect.render` function as a default
dialect render.


## Static queries

Just use t-strings directly. Interpolation parts would be treated as
parameters. The nice part it's quite hard to inject unprocessed data this
way.

```python
>>> date = "2023-01-01"
>>> render(t'SELECT * FROM users WHERE registered > {date}')
('SELECT * FROM users WHERE registered > ?', ['2023-01-01'])

```


## Dynamic queries

Here begins a fun part. We can't use simple binds for dynamic queries.
For example we have a function returning recently registered users:

```python
def get_fresh_users(registered_since: datetime):
    query = t'''\
        SELECT * FROM users
        WHERE registered > {registered_since}
        ORDER BY registered
    '''
    return execute_query(query)
```

And later there is a new requirement for the function. It should return only
enabled or only disabled users if corresponding argument is passed.

```python
def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    if enabled is not None:
        enabled_filter = t' AND enabled = {enabled}'
    else:
        enabled_filter = t''

    query = t'''\
        SELECT * FROM users
        WHERE registered > {registered_since} {enabled_filter}
        ORDER BY registered
    '''
    return execute_query(query)
```

It looks almost fine. You have to use t-string for `enabled_filter`
as well otherwise `query` would treat it as a string parameter. From safety perspective it's great.
But you can predict where we are going. Another one or two additional filters and it would be a complete mess.
Take note how `WHERE` lost `AND` between two filters.


### Conditional markers

`sqlbind_t.cond` injects a special `UNDEFINED` value on false condition and forces template
to return an empty string on rendering. UNDEFINED values are processed per
template instance, for example if some template A includes another nested
template B and B contains UNDEFINED value then only B would be rendered as
empty string.

```python
>>> enabled = True
>>> render(t'AND enabled = {cond(enabled is not None)/enabled}')
('AND enabled = ?', [True])
>>> enabled = None
>>> render(t'AND enabled = {cond(enabled is not None)/enabled}')
('', [])

```

`cond` is a generic form. To remove a repetition (`enabled is not
None`/`enabled`) when value is used both in a condition and as a parameter
value there are two helpers for most common cases:

* `sqlbind_t.not_none`: to check value is not None.
* `sqlbind_t.truthy`: to check value's trueness (`bool(value) is True`).

```python
>>> enabled = True
>>> render(t'AND enabled = {not_none/enabled}')
('AND enabled = ?', [True])
>>> enabled = None
>>> render(t'AND enabled = {not_none/enabled}')
('', [])

```

Let's try it in the function:

```python
from sqlbind_t import not_none

def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    enabled_filter = t'AND enabled = {not_none/enabled}'

    query = t'''\
        SELECT * FROM users
        WHERE registered > {registered_since} {enabled_filter}
        ORDER BY registered
    '''
    return execute_query(query)
```

Hmm. But really nothing was changed. You could write previous code with ternary
if/else and it would look the same from semantic standpoint. Maybe use it
inline?


```python
from sqlbind_t import not_none

def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    query = t'''\
        SELECT * FROM users
        WHERE registered > {registered_since}
              {t'AND enabled = {not_none/enabled}'}
        ORDER BY registered
    '''
    return execute_query(query)
```

It's somewhat palatable but uses nested t-strings. Let's find some improvements.


### WHERE prepender

One approach is to extract filters outside of the query and use `sqlbind_t.WHERE`
prepender to assemble WHERE expression from non-empty parts.

It could help with readability of long complex filters.

```python
from sqlbind_t import not_none, WHERE

def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    filters = [
        t'registered > {registered_since}',
        t'enabled = {not_none/enabled}',
    ]

    query = t'SELECT * FROM users {WHERE(*filters)} ORDER BY registered'
    return execute_query(query)
```

There are also other prependers: `WITH`, `LIMIT`, `OFFSET`, `GROUP_BY`,
`ORDER_BY`, `SET`. They all omit empty parts or are rendered as
empty string if all parts are empty.


### Expressions

Expressions (`sqlbind_t.E`) allow to drop excessive quoting and generate templated results with infix operators.

Attribute access would render a qualified name:

```python
>>> render(t'{E.field}')
('field', [])
>>> render(t'{E.table.field}')
('table.field', [])

```

Real DB tables/columns could use quite peculiar names. You could use `E(name)`
to construct expression from any string:

```python
>>> render(t'{E('"weird table"."weird column"')}')
('"weird table"."weird column"', [])

```

Expression objects define a set of infix operators allowing to bind a right value:

```python
>>> render(t'{E.field > 10}')
('field > ?', [10])
>>> render(t'{E.table.field == 20}')
('table.field = ?', [20])
>>> render(t'{E('"my column"') != None}')
('"my column" IS NOT NULL', [])
>>> render(t'{E.field <= not_none/None}')  # conditional marks also work!
('', [])
>>> render(t'{E.field.IN(not_none/[10])}') # BTW sqlbind has workaround for SQLite to deal with arrays in IN
('field IN ?', [[10]])

```

It could look like a hack and feel ORM-ish but there is no any
expression trees and tree compilation passes. Expressions
are immediately emit templates with interpolations and simple to reason about.

Let's use expressions with the function:

```python
from sqlbind_t import not_none, WHERE, E

def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    filters = [
        E.registered > registered_since,
        E.enabled == not_none/enabled,
    ]

    query = t'SELECT * FROM users {WHERE(*filters)} ORDER BY registered'
    return execute_query(query)
```

Also you could use `&` operator to join filters to assemble expression without a list:

```python
>>> filters = (E.registered > '2023-01-01') & (E.enabled == not_none/True)
>>> render(WHERE(filters))
('WHERE (registered > ? AND enabled = ?)', ['2023-01-01', True])

```

Technically all infix operators on expressions and majority of `sqlbind-t`
helpers return `sqlbind_t.SQL` instances which define logic operators.
Logic operators themselves return `SQL` instances as well.

```python
>>> type(E.enabled == True)
<class 'sqlbind_t.SQL'>

```

`SQL` type is a thin wrapper around t-string template objects providing
additional methods and operators. To obtain `SQL` instance there is
`sqlbind_t.sql` (from a t-string) and `sqlbind_t.text` (from safe static text) helpers:

```python
>>> sql(t'enabled = {True}')
SQL('enabled = ', Interpolation(True, 'True', None, ''))
>>> text('registered_since IS NOT NULL')
SQL('registered_since IS NOT NULL')

```

Note: Internally `SQL` instances are treated as free from UNDEFINED
interpolations and `sqlbind_t.sql` ensures it. Please avoid calling `SQL`
constructor directly.

All `SQL` instances could be composed with `&`, `|` and `~` (negate) operations:

```python
>>> render(~E.enabled | text('registered_since IS NOT NULL'))
('(NOT enabled OR registered_since IS NOT NULL)', [])

```

Sadly due to python's' precedence rules you have to wrap expressions into
additional parenthesis to make it work.


### Inline filters

What about inlining filters into the query though? You could use
`AND_` (there is also 'OR_') prepender:

```python
from sqlbind_t import not_none, E, AND_

def get_fresh_users(registered_since: datetime, enabled: Optional[bool] = None):
    query = t'''
        SELECT * FROM users
        WHERE registered > {registered_since}
         {AND_(E.enabled == not_none/enabled)}
        ORDER BY registered
    '''
    return execute_query(query)
```

It could be a viable alternative for extracted filters. It looks almost acceptable
without nested t-strings and quoting.

That's it. I have no more tricks to make it more readable or pretty.


### Inline vs extracted filters

Inline expressions scale really bad for a large set of filters especially with
complex boolean logic or heavy on conditional markers. To make it manageable
try to extract as much logic and use only `not_none` conditional marker.

IMHO instead of:

```python
>>> now = None
>>> show_only_enabled = True
>>> query = t'SELECT * FROM users WHERE registered > {(now or datetime.now()) - timedelta(days=30)} {AND_(E.enabled == cond(show_only_enabled)/1)}'

```

please consider to use:

```python
>>> now = None
>>> show_only_enabled = True
>>> registered_since = (now or datetime.now()) - timedelta(days=30)
>>> enabled = 1 if show_only_enabled else None
>>> query = t'SELECT * FROM users WHERE registered > {registered_since} {AND_(E.enabled == not_none/enabled)}'

```

