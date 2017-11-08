from datetime import date, datetime
from decimal import Decimal

from dateutil import parser
from enum import Enum

import sqlalchemy as sa
from sqlalchemy_utils import ChoiceType


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
        if isinstance(val, (str, int, float, bool, list, dict)):
            return val
        # TODO- can't use Enum in py2
        if isinstance(val, Enum):
            return val.value
        if isinstance(val, (date, datetime)):
            return val.isoformat()
        return str(val)

    return {field: get_value(val) for field, val in dict_.items()}


def get_default_from_serializable(model_cls):
    col_dict = {
        col.name: col
        for col in model_cls.__table__.columns
    }

    def default_from_serializable(dict_):
        """ Convert serialized field-values dict into values that can be
            supplied to a sqlalchemy object
        """
        def get_value(field, val):
            if val is None:
                return None

            col = col_dict[field]
            if isinstance(col.type, (sa.Date, sa.DateTime)):
                return parser.parse(val)
            if isinstance(col.type, sa.DECIMAL):
                return Decimal(val)
            if isinstance(col.type, ChoiceType):
                return col.type.type_impl.process_result_value(val, None)

            return val

        return {field: get_value(field, val) for field, val in dict_.items()}

    return default_from_serializable
