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
                'example_model',
                model_cls=example_model,
                get_method_name='get_example_model',
                list_method_name='list_example_models',
                page_method_name='page_example_models',
                count_method_name='count_example_models',
                create_method_name='create_example_model',
                update_method_name='update_example_model',
                delete_method_name='delete_example_model',
            )

        return create_service(ExampleService, 'event_dispatcher')

    def test_end_to_end_with_events(self, service):
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

        assert service.event_dispatcher.call_args_list == [
            call('example_model_created', {'example_model': record_1}),
            call('example_model_created', {'example_model': record_2}),
        ]
        service.event_dispatcher.reset_mock()

        # update id 2
        with entrypoint_hook(
            container, "update_example_model"
        ) as update_example_model:

            result = update_example_model(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == [
            call('example_model_updated', {
                'example_model': updated_record_2,
                'changed': ['name'],
                'before': record_2,
            })
        ]
        service.event_dispatcher.reset_mock()

        # update id 2 with no change
        with entrypoint_hook(
            container, "update_example_model"
        ) as update_example_model:

            result = update_example_model(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == []
        service.event_dispatcher.reset_mock()

        # delete
        with entrypoint_hook(
            container, "delete_example_model"
        ) as delete_example_model:

            result = delete_example_model(1)

        assert service.event_dispatcher.call_args_list == [
            call('example_model_deleted', {'example_model': record_1})
        ]
        service.event_dispatcher.reset_mock()

        # confirm deletion
        with entrypoint_hook(
            container, "list_example_models"
        ) as list_example_models:

            result = list_example_models()
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
                'example_model',
                model_cls=example_model,
                to_event_serializable=lambda obj: {'name': obj.name},
                get_method_name='get_example_model',
                list_method_name='list_example_models',
                page_method_name='page_example_models',
                count_method_name='count_example_models',
                create_method_name='create_example_model',
                update_method_name='update_example_model',
                delete_method_name='delete_example_model',
            )

        return create_service(ExampleService, 'event_dispatcher')

    def test_end_to_end_with_events(self, service):
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

        assert service.event_dispatcher.call_args_list == [
            call(
                'example_model_created',
                {'example_model': {'name': 'Bob Dobalina'}}),
            call(
                'example_model_created',
                {'example_model': {'name': 'Phil Connors'}}),
        ]
        service.event_dispatcher.reset_mock()

        # update id 2
        with entrypoint_hook(
            container, "update_example_model"
        ) as update_example_model:

            result = update_example_model(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == [
            call('example_model_updated', {
                'example_model': {'name': 'Ned Ryerson'},
                'changed': ['name'],
                'before': {'name': 'Phil Connors'},
            })
        ]
        service.event_dispatcher.reset_mock()

        # update id 2 with no change
        with entrypoint_hook(
            container, "update_example_model"
        ) as update_example_model:

            result = update_example_model(2, {'name': 'Ned Ryerson'})
            assert result == updated_record_2

        assert service.event_dispatcher.call_args_list == []
        service.event_dispatcher.reset_mock()

        # delete
        with entrypoint_hook(
            container, "delete_example_model"
        ) as delete_example_model:

            result = delete_example_model(1)

        assert service.event_dispatcher.call_args_list == [
            call(
                'example_model_deleted',
                {'example_model': {'name': 'Bob Dobalina'}})
        ]
        service.event_dispatcher.reset_mock()
