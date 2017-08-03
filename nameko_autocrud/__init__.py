import logging
from datetime import date, datetime
from enum import Enum

from nameko.rpc import rpc
from sqlalchemy_filters import apply_filters

from nameko.extensions import DependencyProvider


logger = logging.getLogger(__name__)


class DBStorage(object):

    def __init__(self, model_cls, session=None):
        self.model_cls = model_cls
        self.session = session

    def _get(self, pk):
        obj = self.query.get(pk)
        if not obj:
            # TODO custom exception here?
            raise ValueError('Not found')
        return obj

    @property
    def query(self):
        return self.session.query(self.model_cls)

    def get(self, pk):
        return self._get(pk)

    def list(self, filters=None, offset=None, limit=None):
        query = self.query
        if filters:
            query = apply_filters(query, filters)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    def count(self, filters=None):
        query = self.query
        if filters:
            query = apply_filters(query, filters)

        return query.count()

    def update(self, pk, data, flush=True, commit=True):
        obj = self._get(pk)
        for key, value in data.items():
            setattr(obj, key, value)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()
        return self.get(pk)

    def create(self, data, flush=True, commit=True):
        obj = self.model_cls(**data)
        self.session.add(obj)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()

        return obj

    def delete(self, pk, flush=True, commit=True):
        obj = self._get(pk)
        self.session.delete(obj)
        if commit:
            self.session.commit()
        elif flush:
            self.session.flush()


class DBManager(object):
    model_cls = None
    methods = ['get', 'list', 'count', 'update', 'create', 'delete']
    entity_name = None
    entity_name_plural = None
    function_names = None
    event_names = None

    def __init__(self, db_storage, dispatcher=None):
        self.db_storage = db_storage
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

    def _dispatch_event(self, event_name, object_data):
        if self.dispatcher:
            # TODO should we use `self.entity_name` or allow to customise?
            self.dispatcher(event_name, {self.entity_name: object_data})
            logger.info('dispatched event: %s', event_name)

    def get(self, pk):
        obj = self.db_storage.get(pk)
        return self.to_serializable(obj)

    def list(self, filters=None, offset=None, limit=None):
        results = self.db_storage.list(
            filters=filters, offset=offset, limit=limit)
        return {
            'results': [self.to_serializable(result) for result in results]
        }

    def count(self, filters=None):
        return self.db_storage.count(filters=filters)

    def update(self, pk, data):
        data = self.from_serializable(data)
        updated_obj = self.db_storage.update(pk, data)
        updated_data = self.to_serializable(updated_obj)
        self._dispatch_event(self.event_names['update'], updated_data)
        return updated_data

    def create(self, data):
        data = self.from_serializable(data)
        created_obj = self.db_storage.create(data)
        created_data = self.to_serializable(created_obj)
        self._dispatch_event(self.event_names['create'], created_data)
        return created_data

    def delete(self, pk):
        deleted_data = self.get(pk)
        self.db_storage.delete(pk)
        self._dispatch_event(self.event_names['delete'], deleted_data)

    @classmethod
    def configure_subclass(
        cls, entity_name=None,
        entity_name_plural=None, model_cls=None, **kwargs
    ):
        """ Creates a pre-configured subclass of this manager class """
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
            'count': 'count_{}'.format(entity_name_plural),
            'create': 'create_{}'.format(entity_name),
            'update': 'update_{}'.format(entity_name),
            'delete': 'delete_{}'.format(entity_name),
        }
        event_names = {
            'create': '{}_created'.format(entity_name),
            'update': '{}_updated'.format(entity_name),
            'delete': '{}_deleted'.format(entity_name),
        }
        cls_properties = {
            'model_cls': model_cls,
            'entity_name': entity_name,
            'entity_name_plural': entity_name_plural,
            'function_names': function_names,
            'event_names': event_names,
        }
        # allow overrides and additional kwargs
        cls_properties.update(kwargs)

        class _Manager(cls):
            pass

        # set configuration as class properties
        for key, value in cls_properties.items():
            setattr(_Manager, key, value)

        return _Manager


class AutoCrudProvider(DependencyProvider):

    def __init__(
        self, session_provider, event_dispatcher_provider=None,
        manager_cls=DBManager, db_storage_cls=DBStorage,
        **db_manager_kwargs
    ):
        # store these providers as a map so they are not seen by nameko
        # as sub-dependencies
        self.dependency_providers = {
            'session': session_provider,
            'event_dispatcher': event_dispatcher_provider
        }
        self.manager_cls = manager_cls
        self.db_storage_cls = db_storage_cls
        self.db_manager_kwargs = db_manager_kwargs

    def bind(self, container, attr_name):
        """
        At bind time, modify the service class to add additional rpc methods.
        """
        service_cls = container.service_cls

        bound = super().bind(container, attr_name)

        # create a manager subclass pre-configured with required settings
        manager_subcls = self.manager_cls.configure_subclass(
            **self.db_manager_kwargs
        )
        bound.manager_subcls = manager_subcls

        def make_manager_fn(fn_name):
            def _fn(self, *args, **kwargs):
                """ This is the RPC method that will run on the service """
                # build a manager using dependencies stored in the context
                autocrud_context = self._autocrud_context[manager_subcls]
                manager = manager_subcls(
                    db_storage=autocrud_context['db_storage'],
                    dispatcher=autocrud_context['event_dispatcher']
                )
                # delegate to the manager function with the same name.
                return getattr(manager, fn_name)(*args, **kwargs)
            return _fn

        for manager_fn_name in manager_subcls.methods:
            rpc_name = manager_subcls.function_names[manager_fn_name]
            manager_fn = make_manager_fn(manager_fn_name)
            setattr(service_cls, rpc_name, manager_fn)
            rpc(manager_fn)

        return bound

    def get_dependency(self, worker_ctx):
        # returns a storage instance without session
        # session is bound to it at worker_setup
        return self.db_storage_cls(self.manager_subcls.model_cls)

    def worker_setup(self, worker_ctx):
        service = worker_ctx.service
        session_attr_name = self.dependency_providers['session'].attr_name
        session = getattr(service, session_attr_name)

        # add required session to the storage
        db_storage = getattr(service, self.attr_name)
        db_storage.session = session

        event_dispatcher = None
        if self.dependency_providers['event_dispatcher']:
            ed_attr_name = (
                self.dependency_providers['event_dispatcher'].attr_name
            )
            event_dispatcher = getattr(service, ed_attr_name)

        # store the storage and dispatcher instances on the service
        service._autocrud_context = getattr(service, '_autocrud_context', {})
        service._autocrud_context[self.manager_subcls] = {
            'db_storage': db_storage,
            'event_dispatcher': event_dispatcher,
        }
