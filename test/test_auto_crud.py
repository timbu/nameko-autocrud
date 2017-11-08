import operator

import pytest
from nameko.extensions import DependencyProvider

from nameko_autocrud import get_dependency_accessor


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
