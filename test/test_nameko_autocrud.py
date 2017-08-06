
import pytest
from nameko.constants import AMQP_URI_CONFIG_KEY
from nameko.testing.services import entrypoint_hook
from nameko_sqlalchemy import DB_URIS_KEY, DatabaseSession
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base

from nameko_autocrud import AutoCrudProvider

DeclBase = declarative_base(name='examplebase')


class ExampleModel(DeclBase):
    __tablename__ = 'example'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class ExampleService(object):
    name = "exampleservice"

    session = DatabaseSession(DeclBase)
    example_model_crud = AutoCrudProvider(session, model_cls=ExampleModel)


@pytest.fixture
def container(container_factory, tmpdir):
    # create a temporary database
    db_uri = 'sqlite:///{}'.format(tmpdir.join("db").strpath)
    engine = create_engine(db_uri)
    ExampleModel.metadata.create_all(engine)

    config = {
        AMQP_URI_CONFIG_KEY: 'memory://dev',
        DB_URIS_KEY: {
            'exampleservice:examplebase': db_uri
        }
    }

    container = container_factory(ExampleService, config)
    container.start()
    return container


@pytest.fixture
def db_session(container):
    return DatabaseSession(DeclBase).bind(container, "session")


def test_end_to_end(container):

    # write through the service
    with entrypoint_hook(
        container, "create_examplemodel"
    ) as create_examplemodel:

        result = create_examplemodel({'id': 1, 'name': 'Bob Dobalina'})
        assert result == {'id': 1, 'name': 'Bob Dobalina'}

        result = create_examplemodel({'id': 2, 'name': 'Phil Connors'})
        assert result == {'id': 2, 'name': 'Phil Connors'}

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
        assert result == {
            'results': [
                {'id': 1, 'name': 'Bob Dobalina'},
                {'id': 2, 'name': 'Phil Connors'}
            ]
        }

    # update id 2
    with entrypoint_hook(
        container, "update_examplemodel"
    ) as update_examplemodel:

        result = update_examplemodel(2, {'name': 'Ned Ryerson'})
        assert result == {'id': 2, 'name': 'Ned Ryerson'}

    # get through the service
    with entrypoint_hook(
        container, "get_examplemodel"
    ) as get_examplemodel:

        result = get_examplemodel(1)
        assert result == {'id': 1, 'name': 'Bob Dobalina'}
        result = get_examplemodel(2)
        assert result == {'id': 2, 'name': 'Ned Ryerson'}

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
        assert result == {'results': [{'id': 2, 'name': 'Ned Ryerson'}]}
