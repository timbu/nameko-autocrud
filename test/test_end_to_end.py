import pytest
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
