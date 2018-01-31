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
        example_crud = AutoCrud(
            'session',
            model_cls=example_model,
            get_method_name='get_example_model',
            list_method_name='list_example_models',
            page_method_name='page_example_models',
            count_method_name='count_example_models',
            create_method_name='create_example_model',
            update_method_name='update_example_model',
            delete_method_name='delete_example_model',
        )

    return create_service(ExampleService)


@pytest.fixture
def service2(create_service, dec_base, example_model):

    class ExampleService(object):
        name = "exampleservice"

        session = DatabaseSession(dec_base)
        example_crud = AutoCrud(
            'session', model_cls=example_model,
            get_method_name='get_example_model',
            list_method_name='_list_example_models',
            create_method_name='create_example_model',
            delete_method_name=None
        )

        @rpc
        def get_example_model(self, id_):
            """ Method should not be overwritten """
            return "hello"

        @rpc
        def list_example_models(self, *args, **kwargs):
            """ Enhancing default method behaviour """
            results = self._list_example_models(*args, **kwargs)
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
        container, "create_example_model"
    ) as create_example_model:

        result = create_example_model(record_1)
        assert result == record_1

        result = create_example_model(record_2)
        assert result == record_2

    # count through the service
    with entrypoint_hook(
        container, "count_example_models"
    ) as count_example_models:

        result = count_example_models()
        assert result == 2

    # list through the service
    with entrypoint_hook(
        container, "list_example_models"
    ) as list_example_models:

        result = list_example_models()
        assert result == [
            record_1,
            record_2
        ]

    # page through the service
    with entrypoint_hook(
        container, "page_example_models"
    ) as page_example_models:

        result = page_example_models(1, 1)
        assert result == {
            'results': [record_1],
            'page_num': 1,
            'num_pages': 2,
            'num_results': 2,
        }

        result = page_example_models(1, 2)
        assert result == {
            'results': [record_2],
            'page_num': 2,
            'num_pages': 2,
            'num_results': 2,
        }

        result = page_example_models(1, 3)
        assert result == {
            'results': [],
            'page_num': 3,
            'num_pages': 2,
            'num_results': 2,
        }

    # update id 2
    with entrypoint_hook(
        container, "update_example_model"
    ) as update_example_model:

        result = update_example_model(2, {'name': 'Ned Ryerson'})
        assert result == updated_record_2

    # get through the service
    with entrypoint_hook(
        container, "get_example_model"
    ) as get_example_model:

        result = get_example_model(1)
        assert result == record_1
        result = get_example_model(2)
        assert result == updated_record_2

    # delete
    with entrypoint_hook(
        container, "delete_example_model"
    ) as delete_example_model:

        result = delete_example_model(1)

    # confirm deletion
    with entrypoint_hook(
        container, "list_example_models"
    ) as list_example_models:

        result = list_example_models()
        assert result == [updated_record_2]


def test_wont_overwrite_service_methods(service2):
    """ service2 already implements a get_example_model method.
        Check it is not replaced with the autocrud version.
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_example_model"
    ) as create_example_model:

        result = create_example_model(record_1)
        assert result == record_1

    # call the get method
    with entrypoint_hook(
        container, "get_example_model"
    ) as get_example_model:
        result = get_example_model(1)
        assert result == 'hello'


def test_enhanced_list_method(service2):
    """ service2 implements an enhanced list_example_models method using a
        custom "list" method name.
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_example_model"
    ) as create_example_model:

        result = create_example_model(record_1)
        assert result == record_1

    # call the list method
    with entrypoint_hook(
        container, "list_example_models"
    ) as list_example_models:
        results = list_example_models()
        assert results[0]['id'] == 1
        assert results[0]['name'] == 'Bob Dobalina'
        assert results[0]['more'] == 'data'


def test_delete_method_not_implemented(service2):
    """ service2 switches off delete_example_model
    """
    container = service2.container

    record_1 = {'id': 1, 'name': 'Bob Dobalina'}

    # write through the service
    with entrypoint_hook(
        container, "create_example_model"
    ) as create_example_model:

        result = create_example_model(record_1)
        assert result == record_1

    with pytest.raises(ExtensionNotFound):
        with entrypoint_hook(
            container, "delete_example_model"
        ) as delete_example_model:
            delete_example_model(1)
