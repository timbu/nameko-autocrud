import pytest
from mock import call

from nameko.events import EventDispatcher
from nameko.testing.services import entrypoint_hook
from nameko_sqlalchemy import DatabaseSession

from nameko_autocrud import AutoCrudWithEvents


class TestEndToEndWithEvents:

    @pytest.fixture
    def service(self, create_service, dec_base, example_model):

        class ExampleService(object):
            name = "exampleservice"

            session = DatabaseSession(dec_base)
            event_dispatcher = EventDispatcher()

            example_crud = AutoCrudWithEvents(
                'session',
                'event_dispatcher',
                model_cls=example_model,
            )

        return create_service(ExampleService, 'event_dispatcher')

    def test_end_to_end_with_events(self, service):
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

        assert service.event_dispatcher.call_args_list == [
            call('examplemodel_created', {'examplemodel': record_1}),
            call('examplemodel_created', {'examplemodel': record_2}),
        ]
        service.event_dispatcher.reset_mock()

        # update id 2
        with entrypoint_hook(
            container, "update_examplemodel"
        ) as update_examplemodel:

            result = update_examplemodel(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == [
            call('examplemodel_updated', {
                'examplemodel': updated_record_2,
                'changed': ['name'],
                'before': record_2,
            })
        ]
        service.event_dispatcher.reset_mock()

        # update id 2 with no change
        with entrypoint_hook(
            container, "update_examplemodel"
        ) as update_examplemodel:

            result = update_examplemodel(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == []
        service.event_dispatcher.reset_mock()

        # delete
        with entrypoint_hook(
            container, "delete_examplemodel"
        ) as delete_examplemodel:

            result = delete_examplemodel(1)

        assert service.event_dispatcher.call_args_list == [
            call('examplemodel_deleted', {'examplemodel': record_1})
        ]
        service.event_dispatcher.reset_mock()

        # confirm deletion
        with entrypoint_hook(
            container, "list_examplemodels"
        ) as list_examplemodels:

            result = list_examplemodels()
            assert result == [updated_record_2]


class TestEndToEndWithEventsCustomEventSerializer:

    @pytest.fixture
    def service(self, create_service, dec_base, example_model):

        class ExampleService(object):
            name = "exampleservice"

            session = DatabaseSession(dec_base)
            event_dispatcher = EventDispatcher()

            example_crud = AutoCrudWithEvents(
                'session',
                'event_dispatcher',
                model_cls=example_model,
                to_event_serializable=lambda obj: {'name': obj.name}
            )

        return create_service(ExampleService, 'event_dispatcher')

    def test_end_to_end_with_events(self, service):
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

        assert service.event_dispatcher.call_args_list == [
            call(
                'examplemodel_created',
                {'examplemodel': {'name': 'Bob Dobalina'}}),
            call(
                'examplemodel_created',
                {'examplemodel': {'name': 'Phil Connors'}}),
        ]
        service.event_dispatcher.reset_mock()

        # update id 2
        with entrypoint_hook(
            container, "update_examplemodel"
        ) as update_examplemodel:

            result = update_examplemodel(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == [
            call('examplemodel_updated', {
                'examplemodel': {'name': 'Ned Ryerson'},
                'changed': ['name'],
                'before': {'name': 'Phil Connors'},
            })
        ]
        service.event_dispatcher.reset_mock()

        # update id 2 with no change
        with entrypoint_hook(
            container, "update_examplemodel"
        ) as update_examplemodel:

            result = update_examplemodel(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == []
        service.event_dispatcher.reset_mock()

        # delete
        with entrypoint_hook(
            container, "delete_examplemodel"
        ) as delete_examplemodel:

            result = delete_examplemodel(1)

        assert service.event_dispatcher.call_args_list == [
            call(
                'examplemodel_deleted',
                {'examplemodel': {'name': 'Bob Dobalina'}})
        ]
        service.event_dispatcher.reset_mock()
