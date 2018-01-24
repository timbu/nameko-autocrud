import logging
import math

logger = logging.getLogger(__name__)


class CrudManager(object):

    def __init__(
        self, provider, service, db_storage=None,
        to_serializable=None,
        from_serializable=None,
    ):
        self.db_storage = db_storage
        self.to_serializable = to_serializable
        self.from_serializable = from_serializable

    def get(self, pk):
        obj = self.db_storage.get(pk)
        return self.to_serializable(obj)

    def list(self, filters=None, order_by=None, offset=None, limit=None):
        results = self.db_storage.list(
            filters=filters, order_by=order_by, offset=offset, limit=limit
        )
        return [self.to_serializable(result) for result in results]

    def page(self, page_size, page_num, filters=None, order_by=None):
        if page_size < 1:
            raise ValueError('Invalid page_size ({})'.format(page_size))
        if page_num < 1:
            raise ValueError('Invalid page_num ({})'.format(page_num))

        offset = page_size * (page_num - 1)
        limit = page_size
        total = self.count(filters=filters)
        num_pages = math.ceil(total / page_size)
        results = self.list(
            filters=filters, order_by=order_by, offset=offset, limit=limit
        )
        return {
            'results': results,
            'num_pages': num_pages,
            'num_results': total,
            'page_num': page_num,
        }

    def count(self, filters=None):
        return self.db_storage.count(filters=filters)

    def update(self, pk, data):
        data = self.from_serializable(data)
        updated_obj = self.db_storage.update(pk, data)
        updated_data = self.to_serializable(updated_obj)
        return updated_data

    def _create_object(self, data):
        data = self.from_serializable(data)
        return self.db_storage.create(data)

    def create(self, data):
        created_obj = self._create_object(data)
        return self.to_serializable(created_obj)

    def delete(self, pk):
        deleted_data = self.get(pk)
        self.db_storage.delete(pk)
        return deleted_data


class CrudManagerWithEvents(CrudManager):

    def __init__(
        self, provider, service,
        event_entity_name=None, dispatcher_accessor=None,
        create_event_name=None, update_event_name=None, delete_event_name=None,
        to_event_serializable=None, **kwargs
    ):
        super(CrudManagerWithEvents, self).__init__(
            provider, service, **kwargs)

        self.event_entity_name = event_entity_name
        self.dispatcher = dispatcher_accessor(service)
        self.to_event_serializable = (
            to_event_serializable or self.to_serializable
        )
        self.create_event_name = create_event_name
        self.update_event_name = update_event_name
        self.delete_event_name = delete_event_name

    def _dispatch_event(self, event_name, object_data, payload=None):
        if event_name:
            payload = payload or {}
            payload.update({self.event_entity_name: object_data})
            self.dispatcher(event_name, payload)
            logger.info('dispatched event: %s', event_name)

    def update(self, pk, data):
        before_obj = self.db_storage.get(pk)
        before_data = self.to_event_serializable(before_obj)

        updated_data = super(CrudManagerWithEvents, self).update(pk, data)

        after_obj = self.db_storage.get(pk)
        after_data = self.to_event_serializable(after_obj)

        if before_data != after_data:
            changed = [
                field for field in sorted(set(before_data).union(after_data))
                if before_data.get(field) != after_data.get(field)
            ]
            payload = {'changed': changed, 'before': before_data}
            self._dispatch_event(
                self.update_event_name, after_data, payload=payload
            )

        return updated_data

    def create(self, data):
        created_obj = super(CrudManagerWithEvents, self)._create_object(data)
        event_data = self.to_event_serializable(created_obj)
        self._dispatch_event(self.create_event_name, event_data)
        return self.to_serializable(created_obj)

    def delete(self, pk):
        before_obj = self.db_storage.get(pk)
        before_event = self.to_event_serializable(before_obj)
        deleted_data = super(CrudManagerWithEvents, self).delete(pk)
        self._dispatch_event(self.delete_event_name, before_event)
        return deleted_data
