import operator

import pytest
from nameko.extensions import DependencyProvider

from nameko_autocrud import (
    get_dependency_accessor, AutoCrud, AutoCrudWithEvents,
    CrudManager, DBStorage
)


class TestDependencyAccessor:

    @pytest.fixture
    def service(self):
        class Service:
            def __init__(self):
                self.my_dependency = 'Foo'

        return Service()

    def test_accessor_is_string(self, service):
        accessor = get_dependency_accessor('my_dependency')
        assert accessor(service) == 'Foo'

    def test_accessor_is_dependency_provider(self, service):

        class MyDependencyProvider(DependencyProvider):
            attr_name = 'my_dependency'

        accessor = get_dependency_accessor(MyDependencyProvider())
        assert accessor(service) == 'Foo'

    def test_accessor_is_operator_getter(self, service):
        accessor = get_dependency_accessor(
            operator.attrgetter('my_dependency')
        )
        assert accessor(service) == 'Foo'


class TestRequiredParams:

    @pytest.mark.parametrize(
        'missing', [
            'session_provider', 'model_cls', 'manager_cls', 'db_storage_cls'
        ]
    )
    def test_autocrud_missing_params(self, example_model, missing):
        session_provider = None if missing == 'session_provider' else 'session'
        model_cls = None if missing == 'model_cls' else example_model
        manager_cls = None if missing == 'manager_cls' else CrudManager
        db_storage_cls = None if missing == 'db_storage_cls' else DBStorage

        with pytest.raises(ValueError) as exc:
            AutoCrud(
                session_provider,
                model_cls=model_cls,
                manager_cls=manager_cls,
                db_storage_cls=db_storage_cls,
            )
        assert missing in str(exc)

    @pytest.mark.parametrize(
        'missing', [
            'session_provider', 'model_cls', 'manager_cls', 'db_storage_cls',
            'dispatcher_provider', 'event_entity_name'
        ]
    )
    def test_autocrud_events_missing_params(self, example_model, missing):
        session_provider = None if missing == 'session_provider' else 'session'
        model_cls = None if missing == 'model_cls' else example_model
        manager_cls = None if missing == 'manager_cls' else CrudManager
        db_storage_cls = None if missing == 'db_storage_cls' else DBStorage
        dispatcher_provider = None if missing == 'dispatcher_provider' else 'D'
        event_entity_name = None if missing == 'event_entity_name' else 'exmpl'

        with pytest.raises(ValueError) as exc:
            AutoCrudWithEvents(
                session_provider,
                dispatcher_provider,
                event_entity_name,
                model_cls=model_cls,
                manager_cls=manager_cls,
                db_storage_cls=db_storage_cls,
            )
        assert missing in str(exc)
