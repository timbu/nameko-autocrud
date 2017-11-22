from sqlalchemy import func, inspect
from sqlalchemy_filters import apply_filters, apply_sort


class NotFound(LookupError):
    pass


class DBStorage(object):

    def __init__(self, model_cls, session=None):
        self.model_cls = model_cls
        self.session = session

    def _get(self, pk):
        obj = self.query.get(pk)
        if not obj:
            raise NotFound(
                '{} with ID {} does not exist'
                .format(self.model_cls.__name__, pk))
        return obj

    @property
    def query(self):
        return self.session.query(self.model_cls)

    def get(self, pk):
        return self._get(pk)

    def list(self, filters=None, order_by=None, offset=None, limit=None):
        query = self.query
        if filters:
            query = apply_filters(query, filters)
        if order_by:
            query = apply_sort(query, order_by)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count(self, filters=None):
        # Prefer func.count rather than query.count() for speed
        # .count is inefficient for wide tables, but it could be we make use
        # of another mechanism to stop sqlalchemy querying all fields
        pk_col_names = tuple(
            c.name for c in inspect(self.model_cls).primary_key)
        attr_to_count = getattr(self.model_cls, pk_col_names[0])
        query = self.session.query(func.count(attr_to_count))
        if filters:
            query = apply_filters(query, filters)
        return query.one()[0]

    def update(self, pk, data, flush=True, commit=True):
        obj = self._get(pk)
        for key, value in data.items():
            setattr(obj, key, value)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()
            self.session.refresh(obj)
        return obj

    def create(self, data, flush=True, commit=True):
        obj = self.model_cls(**data)
        self.session.add(obj)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()
            self.session.refresh(obj)

        return obj

    def delete(self, pk, flush=True, commit=True):
        obj = self._get(pk)
        self.session.delete(obj)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()
