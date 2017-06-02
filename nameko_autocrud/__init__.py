from datetime import date, datetime
from enum import Enum

from nameko.extensions import DependencyProvider
from nameko.rpc import rpc
from sqlalchemy.inspection import inspect
from sqlalchemy_filters import apply_filters


class DBManager:

    model_cls = None
    entity_name = None
    entity_name_plural = None
    function_names = None
    event_names = None
    session_attr_name = None
    dispatcher_attr_name = None

    def __init__(self, session=None, dispatcher=None):
        self.session = session
        self.dispatcher = dispatcher

    def to_serializable(self, obj):
        try:
            dict_ = obj.to_dict()
        except AttributeError:
            dict_ = {
                col.name: getattr(obj, col.name)
                for col in obj.__table__.columns
            }

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
            if isinstance(val, (list, set, tuple)):
                return [get_value(v) for v in val]
            if isinstance(val, dict):
                return {k: get_value(v) for k, v in val.items()}
            return str(val)

        return get_value(dict_)

    def from_serializable(self, dict_):
        # default case, we let the sqlalchemy models handle string to
        # date/decimal
        # conversion etc. themselves
        return dict_

    def _get(self, pk):
        obj = self.query.get(pk)
        if not obj:
            # TODO custom exception here?
            raise ValueError('Not found')
        return obj

    def _dispatch_event(self, event_name, object_data):
        if self.dispatcher:
            # TODO should we use `self.entity_name` or allow to customise?
            self.dispatcher(event_name, {self.entity_name: object_data})

    @property
    def query(self):
        return self.session.query(self.model_cls)

    def get(self, pk):
        obj = self._get(pk)
        return self.to_serializable(obj)

    def list(self, filters=None, offset=None, limit=None):
        query = self.query
        if filters:
            query = apply_filters(query, filters)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return {
            'results': [self.to_serializable(obj) for obj in query.all()]
        }

    def update(self, pk, data):
        data = self.from_serializable(data)
        obj = self._get(pk)
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.commit()

        updated_data = self.get(pk)
        self._dispatch_event(self.event_names['update'], updated_data)
        return updated_data

    def create(self, data):
        data = self.from_serializable(data)
        obj = self.model_cls(**data)
        self.session.add(obj)
        self.session.commit()
        pk = inspect(obj).identity

        created_data = self.get(pk)
        self._dispatch_event(self.event_names['create'], created_data)
        return created_data

    def delete(self, pk):
        obj = self._get(pk)
        deleted_data = self.to_serializable(obj)

        self.session.delete(obj)
        self.session.commit()

        self._dispatch_event(self.event_names['delete'], deleted_data)

    @classmethod
    def from_service(cls, service):
        """Instantiate this class, providing any necessary dependencies """
        return cls(
            session=getattr(service, cls.session_attr_name),
            dispatcher=(
                getattr(service, cls.dispatcher_attr_name)
                if cls.dispatcher_attr_name
                else None
            ),
        )

    @classmethod
    def configure_subclass(
        cls, model_cls, session_attr_name='session',
        dispatcher_attr_name=None, entity_name=None,
        entity_name_plural=None, **kwargs
    ):
        """ Creates a pre-configured subclass of this manager """
        entity_name = entity_name or model_cls.__name__.lower()
        entity_name_plural = (
            entity_name_plural or '{}s'.format(entity_name)
        )

        # define the functions this manager provides, and the default names
        # that should be used to access them
        # this map can be overridden in the kwargs
        function_names = {
            'get': 'get_{}'.format(entity_name),
            'list': 'list_{}'.format(entity_name_plural),
            'create': 'create_{}'.format(entity_name),
            'update': 'update_{}'.format(entity_name),
            'delete': 'delete_{}'.format(entity_name),
        }
        event_names = {
            'create': '{}_created'.format(entity_name),
            'update': '{}_updated'.format(entity_name),
            'delete': '{}_deleted'.format(entity_name),
        }
        cls_kwargs = {
            'model_cls': model_cls,
            'session_attr_name': session_attr_name,
            'dispatcher_attr_name': dispatcher_attr_name,
            'entity_name': entity_name,
            'entity_name_plural': entity_name_plural,
            'function_names': function_names,
            'event_names': event_names,
        }
        # allow overrides and additional kwargs
        cls_kwargs.update(kwargs)

        class _Manager(cls):
            pass

        # set configuration as class properties
        for key, value in cls_kwargs.items():
            setattr(_Manager, key, value)

        return _Manager


class AutoCrudProvider(DependencyProvider):

    DEFAULT_METHODS = ['get', 'list', 'update', 'create', 'delete']

    def __init__(
        self, model_cls, methods=DEFAULT_METHODS, manager_cls=DBManager,
        **db_manager_kwargs
    ):
        self.model_cls = model_cls
        self.manager_cls = manager_cls
        self.methods = methods
        self.db_manager_kwargs = db_manager_kwargs

    def bind(self, container, attr_name):
        """
        At bind time, modify the service class to add additional rpc methods.
        """

        service_cls = container.service_cls
        model_cls = self.model_cls

        manager_cls = self.manager_cls.configure_subclass(
            model_cls,
            **self.db_manager_kwargs
        )

        def make_manager_fn(fn_name):
            def _fn(self, *args, **kwargs):
                manager = manager_cls.from_service(self)
                return getattr(manager, fn_name)(*args, **kwargs)
            return _fn

        for manager_fn_name in self.methods:

            rpc_name = manager_cls.function_names[manager_fn_name]

            manager_fn = make_manager_fn(manager_fn_name)
            setattr(service_cls, rpc_name, manager_fn)
            rpc(manager_fn)

        return super().bind(container, attr_name)
