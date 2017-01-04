from copy import deepcopy
from datetime import date, datetime
from enum import Enum

from nameko.rpc import rpc
from sqlalchemy.inspection import inspect


def object_to_dict(obj):
    # TODO maybe check for a serialize method on the model?
    return {
        key: val
        for key, val in obj.__dict__.items()
        if not key.startswith('_')
    }


def make_serializable(dict_):
    # TODO - Maybe some sort of marshmallow schema instead?
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
        if isinstance(val, list):
            return [get_value(v) for v in val]
        if isinstance(val, dict):
            return {k: get_value(v) for k, v in val.items()}
        return str(val)
    return get_value(dict_)


class DBManager:
    model = None

    def __init__(self, session=None):
        self.session = session

    @property
    def query(self):
        return self.session.query(self.model)

    def _get(self, pk):
        obj = self.query.get(pk)
        if not obj:
            # TODO custom exception here
            raise ValueError('Not found')
        return obj

    def get(self, pk):
        obj = self._get(pk)
        # maybe an auto schema?
        return make_serializable(object_to_dict(obj))

    def list(self, filters=None):
        # TODO use sqlalchemy-filters
        objs = self.query.all()
        # maybe an auto schema?
        return {
            'results': [
                make_serializable(object_to_dict(obj)) for obj in objs
            ]
        }

    def update(self, pk, data):
        # TODO need to deserialize and validate
        obj = self._get(pk)
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.commit()

    def create(self, data):
        # TODO need to deserialize and validate
        obj = self.model(**data)
        self.session.add(obj)
        self.session.commit()
        pk = inspect(obj).identity
        return self.get(pk)

    def delete(self, pk):
        obj = self._get(pk)
        self.session.delete(obj)
        self.session.commit()


def db_manager_factory(model_cls):
    class _DBManager(DBManager):
        model = model_cls
    return _DBManager


def autocrud_factory(config):
    """
    Config e.g. ::

        {
            'session_dependency': {
                'provider': DatabaseSession(Base),
                'name': 'session',
            }
            'crud_models': [
                {
                    'model_cls': FeatureFlag,
                    'methods': [
                        {
                            'name': 'get_feature_flag',
                            'manager_fn': 'get'
                        },
                        {
                            'name': 'list_feature_flags',
                            'manager_fn': 'list'
                        },
                        {
                            'name': 'update_feature_flag',
                            'manager_fn': 'update'
                        },
                        {
                            'name': 'create_feature_flag',
                            'manager_fn': 'create'
                        },
                        {
                            'name': 'delete_feature_flag',
                            'manager_fn': 'delete'
                        },
                    ],
                },
                {
                    'manager_cls': <set if overriding default DBManager>,
                    'model_cls': SyncMapping,
                    'methods': [
                        {
                            'name': 'get_sync_mapping',
                            'manager_fn': 'get'
                        },
                        {
                            'name': 'list_sync_mappings',
                            'manager_fn': 'list'
                        }
                    ],
                },

                # Using all defaults:
                {'model_cls': MyModel},

                # Using method defaults with corrected naming:
                {
                    'model_cls': FooStatus,
                    'entity_name': 'foo_status',
                    'entity_name_plural': 'foo_statuses',
                },
            ]
        }

    """
    # from types import MethodType < for python2?

    config = _apply_defaults(config)

    class AutoCrud:
        pass

    # Default to using a service dependency called `session`
    # but this can be customised
    session_attr_name = config['session_dependency']['name']
    session_dependency = config['session_dependency']['dependency']
    if session_dependency:
        setattr(AutoCrud, session_attr_name, session_dependency)

    def make_manager_fn(manager_cls, fn_name):
        def _fn(self, *args, **kwargs):
            manager = manager_cls(session=getattr(self, session_attr_name))
            return getattr(manager, fn_name)(*args, **kwargs)
        return _fn

    for crud_model in config['crud_models']:
        model_cls = crud_model['model_cls']
        manager_cls = (
            crud_model.get('manager_cls') or db_manager_factory(model_cls)
        )

        for crud_method in crud_model['methods']:
            rpc_name = crud_method['name']
            manager_fn_name = crud_method['manager_fn']
            manager_fn = make_manager_fn(manager_cls, manager_fn_name)
            setattr(AutoCrud, rpc_name, manager_fn)
            rpc(manager_fn)

    return AutoCrud


def _apply_defaults(config):
    # set defaults for config
    config = deepcopy(config)
    for crud_model in config['crud_models']:
        model_cls = crud_model['model_cls']
        entity_name = (
            crud_model.get('entity_name') or model_cls.__name__.lower()
        )
        entity_name_plural = (
            crud_model.get('entity_name_plural') or '{}s'.format(entity_name)
        )

        # if no methods, use the default full set
        if 'methods' not in crud_model:
            crud_model['methods'] = [
                {'manager_fn': 'get'},
                {'manager_fn': 'list'},
                {'manager_fn': 'update'},
                {'manager_fn': 'create'},
                {'manager_fn': 'delete'},
            ]
        # if no method names, set to defaults (based on entity_name)
        for crud_method in crud_model['methods']:
            if not crud_method.get('name'):
                if crud_method['manager_fn'] == 'list':
                    crud_method['name'] = 'list_{}'.format(entity_name_plural)
                else:
                    crud_method['name'] = '{}_{}'.format(
                        crud_method['manager_fn'], entity_name
                    )

    session_dependency = config.get('session_dependency') or {}
    config['session_dependency'] = {
        'name': session_dependency.get('name') or 'session',
        'dependency': session_dependency.get('dependency')
    }
    return config


class AutoCrudMetaclass(type):

    def __init__(self, name, bases, clsdict):
        cls = self

        if len(cls.mro()) == 3:
            # only works for direct subclasses

            session_attr_name = cls.crud_session_attr_name

            def make_manager_fn(manager_cls, fn_name):
                def _fn(self, *args, **kwargs):
                    manager = manager_cls(
                        session=getattr(self, session_attr_name)
                    )
                    return getattr(manager, fn_name)(*args, **kwargs)
                return _fn

            model_cls = cls.crud_model_cls
            manager_cls = (
                cls.crud_manager_cls or db_manager_factory(model_cls)
            )

            entity_name = cls.crud_entity_name or model_cls.__name__.lower()
            entity_name_plural = (
                cls.crud_entity_name_plural or '{}s'.format(entity_name)
            )

            for crud_method in cls.crud_methods:
                manager_fn_name = crud_method['manager_fn']

                if manager_fn_name == 'list':
                    auto_name = 'list_{}'.format(entity_name_plural)
                else:
                    auto_name = '{}_{}'.format(manager_fn_name, entity_name)
                rpc_name = crud_method.get('name') or auto_name

                manager_fn = make_manager_fn(manager_cls, manager_fn_name)
                setattr(cls, rpc_name, manager_fn)
                rpc(manager_fn)

        super(AutoCrudMetaclass, cls).__init__(name, bases, clsdict)


class AutoCrud(metaclass=AutoCrudMetaclass):

    crud_session_attr_name = 'session'
    crud_entity_name = None
    crud_entity_name_plural = None
    crud_model_cls = None
    crud_manager_cls = None
    crud_methods = [
        {'manager_fn': 'get'},
        {'manager_fn': 'list'},
        {'manager_fn': 'update'},
        {'manager_fn': 'create'},
        {'manager_fn': 'delete'},
    ]
