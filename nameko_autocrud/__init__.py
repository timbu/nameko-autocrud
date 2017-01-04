from datetime import date, datetime
from enum import Enum

from nameko.rpc import rpc
from sqlalchemy.inspection import inspect
from nameko.extensions import DependencyProvider


def object_to_dict(obj):
    # TODO maybe check for a serialize method on the model?
    return {
        key: val
        for key, val in obj.__dict__.items()
        if not key.startswith('_')
    }


def make_serializable(dict_):
    # TODO - Maybe some sort of marshmallow schema instead?
    def get_value(val):
        if val is None:
            return None
        if isinstance(val, (str, int, float, bool)):
            return val
        # TODO- can't use Enum in py2
        if isinstance(val, Enum):
            return val.value
        if isinstance(val, (date, datetime)):
            return val.isoformat()
        if isinstance(val, list):
            return [get_value(v) for v in val]
        if isinstance(val, dict):
            return {k: get_value(v) for k, v in val.items()}
        return str(val)
    return get_value(dict_)


class DBManager:
    model = None

    def __init__(self, session=None):
        self.session = session

    @property
    def query(self):
        return self.session.query(self.model)

    def _get(self, pk):
        obj = self.query.get(pk)
        if not obj:
            # TODO custom exception here
            raise ValueError('Not found')
        return obj

    def get(self, pk):
        obj = self._get(pk)
        # maybe an auto schema?
        return make_serializable(object_to_dict(obj))

    def list(self, filters=None):
        # TODO use sqlalchemy-filters
        objs = self.query.all()
        # maybe an auto schema?
        return {
            'results': [
                make_serializable(object_to_dict(obj)) for obj in objs
            ]
        }

    def update(self, pk, data):
        # TODO need to deserialize and validate
        obj = self._get(pk)
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.commit()

    def create(self, data):
        # TODO need to deserialize and validate
        obj = self.model(**data)
        self.session.add(obj)
        self.session.commit()
        pk = inspect(obj).identity
        return self.get(pk)

    def delete(self, pk):
        obj = self._get(pk)
        self.session.delete(obj)
        self.session.commit()


def db_manager_factory(model_cls):
    class _DBManager(DBManager):
        model = model_cls
    return _DBManager


class AutoCrudProvider(DependencyProvider):
    DEFAULT_METHODS = [
        {'manager_fn': 'get'},
        {'manager_fn': 'list'},
        {'manager_fn': 'update'},
        {'manager_fn': 'create'},
        {'manager_fn': 'delete'},
    ]

    def __init__(
        self, model_cls, session_attr_name='session', entity_name=None,
        entity_name_plural=None, manager_cls=None, methods=DEFAULT_METHODS
    ):
        self.model_cls = model_cls
        self.session_attr_name = session_attr_name
        self.entity_name = entity_name
        self.entity_name_plural = entity_name_plural
        self.manager_cls = manager_cls
        self.methods = methods

    def bind(self, container, attr_name):
        """
        At bind time, modify the service class to add additional rpc methods.
        """

        service_cls = container.service_cls
        session_attr_name = self.session_attr_name

        def make_manager_fn(manager_cls, fn_name):
            def _fn(self, *args, **kwargs):
                manager = manager_cls(session=getattr(self, session_attr_name))
                return getattr(manager, fn_name)(*args, **kwargs)
            return _fn

        model_cls = self.model_cls
        manager_cls = (
            self.manager_cls or db_manager_factory(model_cls)
        )

        entity_name = self.entity_name or model_cls.__name__.lower()
        entity_name_plural = (
            self.entity_name_plural or '{}s'.format(entity_name)
        )

        for crud_method in self.methods:
            manager_fn_name = crud_method['manager_fn']

            if manager_fn_name == 'list':
                auto_name = 'list_{}'.format(entity_name_plural)
            else:
                auto_name = '{}_{}'.format(manager_fn_name, entity_name)
            rpc_name = crud_method.get('name') or auto_name

            manager_fn = make_manager_fn(manager_cls, manager_fn_name)
            setattr(service_cls, rpc_name, manager_fn)
            rpc(manager_fn)

        return super().bind(container, attr_name)
