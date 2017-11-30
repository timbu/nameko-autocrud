from collections import namedtuple

import pytest
from nameko_sqlalchemy import DB_URIS_KEY
from nameko.testing.services import replace_dependencies
from nameko.constants import AMQP_URI_CONFIG_KEY
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import create_database, drop_database, database_exists
from sqlalchemy.orm import sessionmaker


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
def multi_pk_model(dec_base):
    class MultiPkModel(dec_base):
        __tablename__ = 'multi_pk'
        id = Column(Integer, primary_key=True)
        name = Column(String, primary_key=True)
        value = Column(Integer)
    return MultiPkModel


@pytest.fixture
def db_uri(tmpdir):
    db_uri = 'sqlite:///{}'.format(tmpdir.join("db").strpath)
    return db_uri


@pytest.fixture
def connection(db_uri, dec_base):
    create_db(db_uri)
    engine = create_engine(db_uri)
    dec_base.metadata.create_all(engine)
    connection = engine.connect()
    dec_base.metadata.bind = engine

    yield connection

    dec_base.metadata.drop_all()
    destroy_database(db_uri)


@pytest.fixture
def session(connection, dec_base):
    session_ = sessionmaker(bind=connection)
    db_session = session_()

    yield db_session

    for table in reversed(dec_base.metadata.sorted_tables):
        db_session.execute(table.delete())

    db_session.commit()
    db_session.close()


def create_db(uri):
    """Drop the database at ``uri`` and create a brand new one. """
    destroy_database(uri)
    create_database(uri)


def destroy_database(uri):
    """Destroy the database at ``uri``, if it exists. """
    if database_exists(uri):
        drop_database(uri)


@pytest.fixture
def config(db_uri):
    return {
        AMQP_URI_CONFIG_KEY: 'memory://dev',
        DB_URIS_KEY: {
            'exampleservice:examplebase': db_uri
        }
    }


@pytest.fixture
def create_service(example_model, container_factory, config, session):

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
