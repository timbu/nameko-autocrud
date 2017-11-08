from datetime import date, datetime
from decimal import Decimal
from enum import Enum

import pytest
import sqlalchemy as sa
from sqlalchemy_utils.types import ChoiceType, JSONType

from nameko_autocrud.serializers import (
    default_to_serializable, get_default_from_serializable
)


class TestDefaultSerialization:

    @pytest.fixture
    def model(self, dec_base):
        class ExampleModel(dec_base):

            class MyEnum(Enum):
                choice_a = 'A'
                choice_b = 'B'

            __tablename__ = 'example'
            int_field = sa.Column(sa.Integer, primary_key=True)
            str_field = sa.Column(sa.String)
            null_field = sa.Column(sa.String)
            bool_field = sa.Column(sa.Boolean)
            float_field = sa.Column(sa.Float)
            date_field = sa.Column(sa.Date)
            datetime_field = sa.Column(sa.DateTime)
            decimal_field = sa.Column(sa.DECIMAL)
            text_field = sa.Column(sa.Text)
            json_dict_field = sa.Column(JSONType)
            json_list_field = sa.Column(JSONType)
            choice_field = sa.Column(ChoiceType(MyEnum, impl=sa.String(25)))

            @property
            def ignore1(self):
                return 'ignore'

            ignore2 = 'ignore'

        return ExampleModel

    def test_default_to_serializable(self, model):

        instance = model(
            int_field=1,
            str_field="Foo",
            null_field=None,
            bool_field=True,
            float_field=11.99,
            date_field=date(2018, 12, 31),
            datetime_field=datetime(2018, 12, 31, 10, 8, 22),
            decimal_field=Decimal('10.99'),
            text_field='Bar',
            json_dict_field={'items': [1, 4, 9]},
            json_list_field=['mr', 'ben'],
            choice_field=model.MyEnum.choice_b
        )

        assert default_to_serializable(instance) == {
            'int_field': 1,
            'str_field': 'Foo',
            'null_field': None,
            'bool_field': True,
            'float_field': 11.99,
            'date_field': '2018-12-31',
            'datetime_field': '2018-12-31T10:08:22',
            'decimal_field': '10.99',
            'text_field': 'Bar',
            'json_dict_field': {'items': [1, 4, 9]},
            'json_list_field': ['mr', 'ben'],
            'choice_field': 'B'
        }

    def test_default_from_serializable(self, model, db_uri, session):

        dict_ = get_default_from_serializable(model)({
            'int_field': 1,
            'str_field': 'Foo',
            'null_field': None,
            'bool_field': True,
            'float_field': 11.99,
            'date_field': '2018-12-31',
            'datetime_field': '2018-12-31T10:08:22',
            'decimal_field': '10.99',
            'text_field': 'Bar',
            'json_dict_field': {'items': [1, 4, 9]},
            'json_list_field': ['mr', 'ben'],
            'choice_field': 'B'
        })

        instance = model(**dict_)
        session.add(instance)
        session.commit()
