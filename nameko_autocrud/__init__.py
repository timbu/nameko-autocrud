import logging

from nameko.rpc import rpc

from nameko.extensions import DependencyProvider

from .managers import CrudManager
from .storage import DBStorage

logger = logging.getLogger(__name__)


class AutoCrudProvider(DependencyProvider):

    def __init__(
        self, session_provider,
        manager_cls=CrudManager, db_storage_cls=DBStorage,
        model_cls=None, entity_name=None, entity_name_plural=None,
        methods=None, method_names=None,
        **crud_manager_kwargs
    ):
        # store these providers as a map so they are not seen by nameko
        # as sub-dependencies
        self.dependency_providers = {
            'session': session_provider,
        }
        self.model_cls = model_cls
        self.manager_cls = manager_cls
        self.db_storage_cls = db_storage_cls
        self.crud_manager_kwargs = crud_manager_kwargs

        self.entity_name = entity_name or model_cls.__name__.lower()
        self.entity_name_plural = (
            entity_name_plural or '{}s'.format(self.entity_name)
        )
        self.methods = methods or [
            'get', 'list', 'count', 'update', 'create', 'delete']

        self.method_names = method_names or {
            'get': 'get_{}'.format(self.entity_name),
            'list': 'list_{}'.format(self.entity_name_plural),
            'count': 'count_{}'.format(self.entity_name_plural),
            'create': 'create_{}'.format(self.entity_name),
            'update': 'update_{}'.format(self.entity_name),
            'delete': 'delete_{}'.format(self.entity_name),
        }

    def bind(self, container, attr_name):
        """
        At bind time, modify the service class to add additional rpc methods.
        """
        service_cls = container.service_cls

        bound = super().bind(container, attr_name)

        def make_manager_fn(fn_name):
            def _fn(self, *args, **kwargs):
                """ This is the RPC method that will run on the service """
                # instantiate a manager instance
                manager = bound.manager_cls(
                    bound,  # the provider
                    self,  # the service instance
                    db_storage=getattr(self, attr_name),
                    **bound.crud_manager_kwargs
                )
                # delegate to the manager method with the same name.
                return getattr(manager, fn_name)(*args, **kwargs)
            return _fn

        for manager_fn_name in self.methods:
            rpc_name = self.method_names[manager_fn_name]
            manager_fn = make_manager_fn(manager_fn_name)
            setattr(service_cls, rpc_name, manager_fn)
            rpc(manager_fn)

        return bound

    def get_dependency(self, worker_ctx):
        # returns a storage instance without session
        # session is bound to it at worker_setup
        return self.db_storage_cls(self.model_cls)

    def worker_setup(self, worker_ctx):
        service = worker_ctx.service
        session_attr_name = self.dependency_providers['session'].attr_name
        session = getattr(service, session_attr_name)

        # add required session to the storage
        db_storage = getattr(service, self.attr_name)
        db_storage.session = session
