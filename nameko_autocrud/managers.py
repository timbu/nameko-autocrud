import logging
from datetime import date, datetime
from enum import Enum


logger = logging.getLogger(__name__)


def default_to_serializable(obj):
    """ Convert a sqlalchemy model instance to a dict ready for serialization.
    """
    try:
        dict_ = obj.to_dict()
    except AttributeError:
        dict_ = {
            col.name: getattr(obj, col.name)
            for col in obj.__table__.columns
        }

    def get_value(val):
        if val is None:
            return None
        if isinstance(val, (str, int, float, bool)):
            return val
        # TODO- can't use Enum in py2
        if isinstance(val, Enum):
            return val.value
        if isinstance(val, (date, datetime)):
            return val.isoformat()
        if isinstance(val, (list, set, tuple)):
            return [get_value(v) for v in val]
        if isinstance(val, dict):
            return {k: get_value(v) for k, v in val.items()}
        return str(val)

    return get_value(dict_)


def default_from_serializable(dict_):
    """ Convert a field-values dict into sqlalchemy model field and values """
    # default case, we let the sqlalchemy models handle string to
    # date/decimal
    # conversion etc themselves
    return dict_


class CrudManager(object):

    def __init__(
        self, provider, service, db_storage=None,
        to_serializable=default_to_serializable,
        from_serializable=default_from_serializable, **kwargs
    ):
        self.db_storage = db_storage
        self.to_serializable = to_serializable
        self.from_serializable = from_serializable

    def get(self, pk):
        obj = self.db_storage.get(pk)
        return self.to_serializable(obj)

    def list(self, filters=None, offset=None, limit=None):
        results = self.db_storage.list(
            filters=filters, offset=offset, limit=limit
        )
        return [self.to_serializable(result) for result in results]

    def count(self, filters=None):
        return self.db_storage.count(filters=filters)

    def update(self, pk, data):
        data = self.from_serializable(data)
        updated_obj = self.db_storage.update(pk, data)
        updated_data = self.to_serializable(updated_obj)
        return updated_data

    def create(self, data):
        data = self.from_serializable(data)
        created_obj = self.db_storage.create(data)
        created_data = self.to_serializable(created_obj)
        return created_data

    def delete(self, pk):
        deleted_data = self.get(pk)
        self.db_storage.delete(pk)
        return deleted_data


class CrudManagerWithEvents(CrudManager):

    def __init__(
        self, provider, service,
        dispatcher_name='event_dispatcher',
        event_names=None, **kwargs
    ):
        super().__init__(provider, service, **kwargs)

        self.entity_name = provider.entity_name
        self.dispatcher = getattr(service, dispatcher_name)
        self.event_names = event_names or {
            'create': '{}_created'.format(provider.entity_name),
            'update': '{}_updated'.format(provider.entity_name),
            'delete': '{}_deleted'.format(provider.entity_name),
        }

    def _dispatch_event(self, event_name, object_data):
        # TODO should we use `self.entity_name` or allow to customise?
        self.dispatcher(event_name, {self.entity_name: object_data})
        logger.info('dispatched event: %s', event_name)

    def update(self, pk, data):
        before = self.get(pk)
        updated_data = super().update(pk, data)
        if updated_data != before:
            self._dispatch_event(self.event_names['update'], updated_data)
        return updated_data

    def create(self, data):
        created_data = super().create(data)
        self._dispatch_event(self.event_names['create'], created_data)
        return created_data

    def delete(self, pk):
        deleted_data = super().delete(pk)
        self._dispatch_event(self.event_names['delete'], deleted_data)
        return deleted_data
