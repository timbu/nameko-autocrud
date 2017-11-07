# Nameko relies on eventlet
# You should monkey patch the standard library as early as possible to avoid
# importing anything before the patch is applied.
# See http://eventlet.net/doc/patching.html#monkeypatching-the-standard-library
# import eventlet
# eventlet.monkey_patch()  # noqa (code before rest of imports)

# from nameko.containers import ServiceContainer
from collections import namedtuple

import pytest
from nameko_sqlalchemy import DB_URIS_KEY
from nameko.testing.services import replace_dependencies
from nameko.constants import AMQP_URI_CONFIG_KEY
from nameko_sqlalchemy import DB_URIS_KEY, DatabaseSession
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base


@pytest.fixture
def dec_base():
    return declarative_base(name='examplebase')


@pytest.fixture
def example_model(dec_base):
    class ExampleModel(dec_base):
        __tablename__ = 'example'
        id = Column(Integer, primary_key=True)
        name = Column(String)
    return ExampleModel


@pytest.fixture
def db_uri(tmpdir, example_model):
    db_uri = 'sqlite:///{}'.format(tmpdir.join("db").strpath)
    engine = create_engine(db_uri)
    example_model.metadata.create_all(engine)

    return db_uri


@pytest.fixture
def config(db_uri):
    return {
        AMQP_URI_CONFIG_KEY: 'memory://dev',
        DB_URIS_KEY: {
            'exampleservice:examplebase': db_uri
        }
    }


@pytest.fixture
def create_service(container_factory, config):

    def _create(service_cls, *dependencies, **dependency_map):

        dependency_names = list(dependencies) + list(dependency_map.keys())

        ServiceMeta = namedtuple(
            'ServiceMeta', ['container'] + dependency_names
        )

        container = container_factory(service_cls, config)

        mocked_dependencies = replace_dependencies(
            container, *dependencies, **dependency_map
        )

        if len(dependency_names) == 1:
            mocked_dependencies = (mocked_dependencies, )

        container.start()

        return ServiceMeta(container, *mocked_dependencies, **dependency_map)

    return _create
