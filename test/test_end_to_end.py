import pytest

from nameko.exceptions import ExtensionNotFound
from nameko.rpc import rpc
from nameko.testing.services import entrypoint_hook
from nameko_sqlalchemy import DatabaseSession

from nameko_autocrud import AutoCrud


@pytest.fixture
def service(create_service, dec_base, example_model):

    class ExampleService(object):
        name = "exampleservice"

        session = DatabaseSession(dec_base)
        example_crud = AutoCrud('session', model_cls=example_model)

    return create_service(ExampleService)


@pytest.fixture
def service2(create_service, dec_base, example_model):

    class ExampleService(object):
        name = "exampleservice"

        session = DatabaseSession(dec_base)
        example_crud = AutoCrud(
            'session', model_cls=example_model,
            list_method_name='_list_examplemodels',
            delete_method_name=None
        )

        @rpc
        def get_examplemodel(self, id_):
            """ Method should not be overwritten """
            return "hello"

        @rpc
        def list_examplemodels(self, *args, **kwargs):
            """ Enhancing default method behaviour """
            results = self._list_examplemodels(*args, **kwargs)
            for result in results:
                result['more'] = 'data'
            return results

    return create_service(ExampleService)


def test_end_to_end(service):
    container = service.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}
    record_2 = {'id': 2, 'name': 'Phil Connors'}
    updated_record_2 = {'id': 2, 'name': 'Ned Ryerson'}

    # write through the service
    with entrypoint_hook(
        container, "create_examplemodel"
    ) as create_examplemodel:

        result = create_examplemodel(record_1)
        assert result == record_1

        result = create_examplemodel(record_2)
        assert result == record_2

    # count through the service
    with entrypoint_hook(
        container, "count_examplemodels"
    ) as count_examplemodels:

        result = count_examplemodels()
        assert result == 2

    # list through the service
    with entrypoint_hook(
        container, "list_examplemodels"
    ) as list_examplemodels:

        result = list_examplemodels()
        assert result == [
            record_1,
            record_2
        ]

    # page through the service
    with entrypoint_hook(
        container, "page_examplemodels"
    ) as page_examplemodels:

        result = page_examplemodels(1, 1)
        assert result == {
            'results': [record_1],
            'page_num': 1,
            'num_pages': 2,
            'num_results': 2,
        }

        result = page_examplemodels(1, 2)
        assert result == {
            'results': [record_2],
            'page_num': 2,
            'num_pages': 2,
            'num_results': 2,
        }

        result = page_examplemodels(1, 3)
        assert result == {
            'results': [],
            'page_num': 3,
            'num_pages': 2,
            'num_results': 2,
        }

    # update id 2
    with entrypoint_hook(
        container, "update_examplemodel"
    ) as update_examplemodel:

        result = update_examplemodel(2, {'name': 'Ned Ryerson'})
        assert result == updated_record_2

    # get through the service
    with entrypoint_hook(
        container, "get_examplemodel"
    ) as get_examplemodel:

        result = get_examplemodel(1)
        assert result == record_1
        result = get_examplemodel(2)
        assert result == updated_record_2

    # delete
    with entrypoint_hook(
        container, "delete_examplemodel"
    ) as delete_examplemodel:

        result = delete_examplemodel(1)

    # confirm deletion
    with entrypoint_hook(
        container, "list_examplemodels"
    ) as list_examplemodels:

        result = list_examplemodels()
        assert result == [updated_record_2]


def test_wont_overwrite_service_methods(service2):
    """ service2 already implements a get_examplemodel method.
        Check it is not replaced with the autocrud version.
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_examplemodel"
    ) as create_examplemodel:

        result = create_examplemodel(record_1)
        assert result == record_1

    # call the get method
    with entrypoint_hook(
        container, "get_examplemodel"
    ) as get_examplemodel:
        result = get_examplemodel(1)
        assert result == 'hello'


def test_enhanced_list_method(service2):
    """ service2 implements an enhanced list_examplemodels method using a
        custom "list" method name.
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_examplemodel"
    ) as create_examplemodel:

        result = create_examplemodel(record_1)
        assert result == record_1

    # call the list method
    with entrypoint_hook(
        container, "list_examplemodels"
    ) as list_examplemodels:
        results = list_examplemodels()
        assert results[0]['id'] == 1
        assert results[0]['name'] == 'Bob Dobalina'
        assert results[0]['more'] == 'data'


def test_delete_method_not_implemented(service2):
    """ service2 switches off delete_examplemodel
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_examplemodel"
    ) as create_examplemodel:

        result = create_examplemodel(record_1)
        assert result == record_1

    with pytest.raises(ExtensionNotFound):
        with entrypoint_hook(
            container, "delete_examplemodel"
        ) as delete_examplemodel:
            delete_examplemodel(1)
