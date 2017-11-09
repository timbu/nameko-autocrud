import pytest

from nameko_autocrud.storage import DBStorage, NotFound


@pytest.fixture
def instances(example_model, session):
    instances_ = [
        example_model(id=1, name='foo'),
        example_model(id=2, name='bar'),
        example_model(id=3, name='baz'),
    ]
    session.add_all(instances_)
    session.commit()
    return instances_


@pytest.fixture
def storage(example_model, session):
    return DBStorage(example_model, session=session)


def get_name_via_query(session, id_):
    results = session.execute(
        'SELECT name FROM example WHERE id = {}'.format(id_)
    ).fetchall()
    if results:
        return results[0][0]
    return None


class TestStorageGet:

    def test_get(self, instances, storage):
        result = storage.get(1)
        assert result == instances[0]

        result = storage.get(3)
        assert result == instances[2]

    def test_not_found(self, instances, storage):
        with pytest.raises(NotFound) as exc:
            storage.get(4)

        assert 'ExampleModel with ID 4 does not exist' in str(exc)


class TestStorageList:

    def test_list(self, instances, storage):
        results = storage.list()
        assert results == instances

    def test_list_filters(self, instances, storage):
        results = storage.list(filters={'field': 'id', 'op': '<', 'value': 3})
        assert results == instances[:2]
        results = storage.list(filters={'field': 'id', 'op': '>', 'value': 1})
        assert results == instances[1:]

    def test_list_offset(self, instances, storage):
        results = storage.list(offset=1)
        assert results == instances[1:]
        results = storage.list(offset=2)
        assert results == instances[2:]
        results = storage.list(offset=3)
        assert results == []

    def test_list_limit(self, instances, storage):
        results = storage.list(limit=1)
        assert results == instances[:1]

    def test_list_offset_limit(self, instances, storage):
        results = storage.list(offset=2, limit=1)
        assert results == [instances[2]]

    def test_list_filters_offset_limit(self, instances, storage):
        results = storage.list(
            filters={'field': 'id', 'op': '<', 'value': 3}, offset=1, limit=1
        )
        assert results == [instances[1]]


class TestStorageCount:

    def test_count(self, instances, storage):
        result = storage.count()
        assert result == 3

    def test_count_filters(self, instances, storage):
        result = storage.count({'field': 'id', 'op': '<', 'value': 3})
        assert result == 2


class TestStorageUpdate:

    def test_update_commit(self, instances, storage, session):
        result = storage.update(1, {'name': 'CHANGE'})
        assert result.name == 'CHANGE'
        session.rollback()
        assert result.name == 'CHANGE'
        assert storage.get(1).name == 'CHANGE'

    def test_update_flush_no_commit(self, instances, storage, session):
        result = storage.update(
            1, {'name': 'CHANGE'}, flush=True, commit=False
        )
        assert result.name == 'CHANGE'
        assert get_name_via_query(session, 1) == 'CHANGE'

        session.rollback()
        assert result.name == 'foo'
        assert storage.get(1).name == 'foo'
        assert get_name_via_query(session, 1) == 'foo'

    def test_update_no_flush_no_commit(self, instances, storage, session):
        result = storage.update(
            1, {'name': 'CHANGE'}, flush=False, commit=False
        )
        assert result.name == 'CHANGE'
        assert get_name_via_query(session, 1) == 'foo'

        session.rollback()
        assert result.name == 'foo'
        assert storage.get(1).name == 'foo'
        assert get_name_via_query(session, 1) == 'foo'

    class TestStorageCreate:

        def test_create_commit(self, instances, storage, session):
            result = storage.create({'id': 4, 'name': 'NEW'})
            assert (result.id, result.name) == (4, 'NEW')

            session.rollback()
            assert (result.id, result.name) == (4, 'NEW')
            assert storage.get(4).name == 'NEW'

        def test_create_flush_no_commit(self, instances, storage, session):
            result = storage.create(
                {'id': 4, 'name': 'NEW'}, flush=True, commit=False)
            assert (result.id, result.name) == (4, 'NEW')
            assert get_name_via_query(session, 4) == 'NEW'

            session.rollback()
            assert storage.count() == 3
            assert get_name_via_query(session, 4) is None

        def test_create_no_flush_no_commit(self, instances, storage, session):
            result = storage.create(
                {'id': 4, 'name': 'NEW'}, flush=False, commit=False)
            assert (result.id, result.name) == (4, 'NEW')
            assert get_name_via_query(session, 4) is None

            session.rollback()
            assert get_name_via_query(session, 4) is None

    class TestStorageDelete:

        def test_delete_commit(self, instances, storage, session):
            storage.delete(2)
            assert storage.list() == [instances[0], instances[2]]
            assert get_name_via_query(session, 2) is None

            session.rollback()
            assert storage.list() == [instances[0], instances[2]]

        def test_delete_flush_no_commit(self, instances, storage, session):
            storage.delete(2, flush=True, commit=False)
            assert storage.list() == [instances[0], instances[2]]
            assert get_name_via_query(session, 2) is None

            session.rollback()
            assert storage.list() == [instances[0], instances[1], instances[2]]
            assert get_name_via_query(session, 2) == 'bar'

        def test_delete_no_flush_no_commit(self, instances, storage, session):
            storage.delete(2, flush=False, commit=False)
            assert storage.list() == [instances[0], instances[2]]
            assert get_name_via_query(session, 2) is None  # TODO check this

            session.rollback()
            assert storage.list() == [instances[0], instances[1], instances[2]]
            assert get_name_via_query(session, 2) == 'bar'
