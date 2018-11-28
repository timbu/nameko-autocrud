import logging

from nameko.rpc import rpc as nameko_rpc
from nameko.extensions import DependencyProvider

from .managers import CrudManager, CrudManagerWithEvents
from .serializers import default_to_serializable, get_default_from_serializable
from .storage import DBStorage
from .storage import NotFound  # noqa

logger = logging.getLogger(__name__)


def get_dependency_accessor(accessor):

    def get_dependency(service):
        if isinstance(accessor, str):
            return getattr(service, accessor)
        if isinstance(accessor, DependencyProvider):
            # only supported in nameko >= 2.7.0
            return getattr(service, accessor.attr_name)
        # assume a operator.getter style callable:
        return accessor(service)

    return get_dependency


class AutoCrud(DependencyProvider):

    def __init__(
        self, session_provider,
        manager_cls=CrudManager, db_storage_cls=DBStorage,
        model_cls=None,
        from_serializable=None, to_serializable=None,
        get_method_name=None, list_method_name=None,
        page_method_name=None, count_method_name=None,
        create_method_name=None, update_method_name=None,
        delete_method_name=None,
        get_rpc=None, list_rpc=None,
        page_rpc=None, count_rpc=None,
        create_rpc=None, update_rpc=None,
        delete_rpc=None,
        rpc=nameko_rpc,
        **crud_manager_kwargs
    ):
        required = [
            (session_provider, 'session_provider'),
            (manager_cls, 'manager_cls'),
            (db_storage_cls, 'db_storage_cls'),
            (model_cls, 'model_cls'),
        ]
        missing = [name for param, name in required if not param]
        if missing:
            raise ValueError(
                '`{}` param(s) are missing for {}'.format(
                    missing, type(self).__name__))

        # store these providers as a map so they are not seen by nameko
        # as sub-dependencies
        self.session_accessor = get_dependency_accessor(session_provider)
        self.model_cls = model_cls
        self.manager_cls = manager_cls
        self.db_storage_cls = db_storage_cls
        self.crud_manager_kwargs = crud_manager_kwargs
        self.rpc = rpc

        self.method_config = {
            'get': (get_method_name, get_rpc),
            'list': (list_method_name, list_rpc),
            'page': (page_method_name, page_rpc),
            'count': (count_method_name, count_rpc),
            'create': (create_method_name, create_rpc),
            'update': (update_method_name, update_rpc),
            'delete': (delete_method_name, delete_rpc),
        }

        self.from_serializable = (
            from_serializable or get_default_from_serializable(model_cls))

        self.to_serializable = (to_serializable or default_to_serializable)

    def bind(self, container, attr_name):
        """
        At bind time, modify the service class to add additional rpc methods.
        """
        service_cls = container.service_cls

        bound = super(AutoCrud, self).bind(container, attr_name)

        def make_manager_fn(fn_name):
            def _fn(self, *args, **kwargs):
                """ This is the RPC method that will run on the service """
                # instantiate a manager instance
                manager = bound.manager_cls(
                    bound,  # the provider
                    self,  # the service instance
                    db_storage=getattr(self, attr_name),
                    from_serializable=bound.from_serializable,
                    to_serializable=bound.to_serializable,
                    **bound.crud_manager_kwargs
                )
                # delegate to the manager method with the same name.
                return getattr(manager, fn_name)(*args, **kwargs)
            return _fn

        for mngr_fn_name, (rpc_name, method_rpc) in self.method_config.items():
            if rpc_name and not getattr(service_cls, rpc_name, None):
                manager_fn = make_manager_fn(mngr_fn_name)
                setattr(service_cls, rpc_name, manager_fn)
                # apply rpc decorator
                rpc = method_rpc or self.rpc
                rpc(manager_fn)

        return bound

    def get_dependency(self, worker_ctx):
        # returns a storage instance without session
        # session is bound to it at worker_setup
        return self.db_storage_cls(self.model_cls)

    def worker_setup(self, worker_ctx):
        service = worker_ctx.service
        session = self.session_accessor(service)

        # add required session to the storage
        db_storage = getattr(service, self.attr_name)
        db_storage.session = session


class AutoCrudWithEvents(AutoCrud):

    def __init__(
        self,
        session_provider,
        dispatcher_provider,
        event_entity_name,
        create_event_name=None,
        update_event_name=None,
        delete_event_name=None,
        manager_cls=CrudManagerWithEvents,
        **kwargs
    ):
        required = [
            (dispatcher_provider, 'dispatcher_provider'),
            (event_entity_name, 'event_entity_name'),
        ]
        missing = [name for param, name in required if not param]
        if missing:
            raise ValueError(
                '`{}` param(s) are missing for {}'.format(
                    missing, type(self).__name__))

        dispatcher_accessor = get_dependency_accessor(dispatcher_provider)
        super(AutoCrudWithEvents, self).__init__(
            session_provider,
            manager_cls=manager_cls,
            dispatcher_accessor=dispatcher_accessor,
            event_entity_name=event_entity_name,
            create_event_name=create_event_name,
            update_event_name=update_event_name,
            delete_event_name=delete_event_name,
            **kwargs
        )
