"""Regression coverage for database-side completion/null filtering."""
import pytest
from sqlalchemy import JSON, Column, Integer, String, cast, create_engine, null, or_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base, sessionmaker


@pytest.mark.parametrize('field,values,expected', [
    ('nightly', [{}, {'complete': False}, {'complete': True}, {'complete': None}], [0, 1, 3]),
    ('satellite', [null(), None, {}, {'status': 'usable'}, {'status': 'insufficient_quality'}, 'null'], [0, 1]),
])
def test_json_filter_preserves_missing_null_and_completed_semantics(field, values, expected):
    base = declarative_base()
    class Row(base):
        __tablename__ = 'synthetic_json'
        id = Column(Integer, primary_key=True)
        value = Column(JSON)
    engine = create_engine('sqlite://')
    base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add_all(Row(id=i, value=value) for i, value in enumerate(values))
        db.commit()
        predicate = (Row.value['complete'].as_boolean().is_not(True) if field == 'nightly' else
            or_(Row.value.is_(None), cast(Row.value, String) == 'null'))
        query = select(Row.id).where(predicate).order_by(Row.id)
        assert list(db.scalars(query)) == expected
        # Production uses PostgreSQL JSON, not JSONB. Avoid JSON equality,
        # which PostgreSQL does not provide for this column type.
        sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
        if field == 'nightly':
            assert 'AS BOOLEAN) IS NOT true' in sql
        else:
            assert 'IS NULL OR CAST(' in sql and "AS VARCHAR) = 'null'" in sql
