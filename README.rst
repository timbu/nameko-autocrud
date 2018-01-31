nameko-autocrud
=================

-  A (slightly magical) dependency to automatically add CRUD RPC (and possibly later HTTP) entrypoints to `nameko <https://github.com/nameko/nameko/>`_ microservices.
-  Based on `Sqlalchemy <http://www.sqlalchemy.org/>`_ models.
-  Aim is to reduce the amount of code required to implement common methods.
-  Uses `sqlalchemy-filters <https://github.com/Overseas-Student-Living/sqlalchemy-filters>`_.
-  Works in conjunction with sqlalchemy dependency providers such as `nameko-sqlalchemy <https://github.com/onefinestay/nameko-sqlalchemy>`_.
-  Each dependency also can be used in other methods to get/manipulate model instances.
-  Customisable components.

Usage
-----

.. code-block:: python

    from nameko_sqlalchemy import DatabaseSession
    from nameko_autocrud import AutoCrud

    class MyService:

        name = 'my_service'
        session = DatabaseSession(models.Base)

        member_auto_crud = AutoCrud(
            session,
            model_cls=models.Member,
            get_method_name='get_member',
            list_method_name='list_members',
            page_method_name='page_members',
            count_method_name='count_members',
            create_method_name='create_member',
            update_method_name='update_member',
            delete_method_name='delete_member',
        )
        payment_auto_crud = AutoCrud(
            session,
            model_cls=models.Payment,
            get_method_name='get_payment',
            list_method_name='list_payments'
        )

        @rpc
        def my_entrypoint(self, value):
            return value + 1


This will automatically make the following additional RPC entrypoints available:

.. code-block:: python

    get_member(self, id_)
    list_members(self, filters=None, offset=None, limit=None, order_by=None)
    page_members(self, page_size, page_num, filters=None, order_by=None)
    count_members(self, filters=None)
    update_member(self, id_, data)
    create_member(self, data)
    delete_member(self, id_)
    get_payment(self, id_)
    list_payments(self, filters=None, offset=None, limit=None, order_by=None)


The dependencies themselves can be used to manipulate sqlalchemy objects within other code E.g.

.. code-block:: python

    @rpc
    def copy_member_name(self, from_id, to_id):
        member = self.member_auto_crud.get(from_id)
        self.member_auto_crud.update(to_id, {'name': member.name})


Customizing
===========

Setting method names
------------------------

The ``*_method_name`` kwargs are used to declare the name of each crud method. Setting this value to `None` (or not providing the kwarg) will prevent the method from being generated.

.. code-block:: python

    cake_crud = AutoCrud(
        session, model_cls=models.Cake,
        delete_method_name='eat_cake',
        update_method_name=None,
    )

Customizing serialization
-------------------------

TODO - marshmallow examples


Events
======
Nameko-autocrud includes an additional ``AutoCrudWithEvents`` DependencyProvider. This has the same behaviour as ``AutoCrud`` but can dispatch nameko events for ``create``, ``update`` & ``delete`` actions.

.. code-block:: python

    from nameko.events import EventDispatcher
    from nameko_sqlalchemy import DatabaseSession
    from nameko_autocrud import AutoCrudWithEvents

    class MyService:

        name = 'my_service'
        session = DatabaseSession(models.Base)
        dispatcher = EventDispatcher()

        payment_auto_crud = AutoCrudWithEvents(
            session, dispatcher, 'payment',
            model_cls=models.Payment,
            create_event_name='payment_created',
            update_event_name='payment_updated',
            delete_event_name='payment_deleted',
            create_method_name='create_payment',
            update_method_name='update_payment',
            delete_method_name='delete_payment',
        )

Nameko events will be generated for every ``*_even_name`` parameter given. If the parameter is set to ``None`` or not present, the event will not be dispatched. 

Create events
-------------
Create events will be dispatched after a successful creation. The event-name is given by ``create_event_name`` and the payload will be of the form:

.. code-block:: python

    {
        'payment': {<serialized payment instance after creation>}
    }

Where the ``payment`` key is given by the required ``event_entity_name`` parameter.

Update events
-------------
Update events will be dispatched after a successful update that resulted in changes. The event-name is given by ``update_event_name`` and the payload will be of the form:

.. code-block:: python

    {
      'payment': {<serialized payment instance after the update>},
      'changed': [<list of the changed fields>],
      'before': {<serialized payment instance before the update>},
    }

Where the ``payment`` key is given by the required ``event_entity_name`` parameter.

Delete events
-------------
Delete events will be dispatched after a successful deletion. The event-name is given by ``delete_event_name`` and the payload will be of the form:

.. code-block:: python

    {
        'payment': {<serialized payment instance before deletion>}
    }

Where the ``payment`` key is given by the required ``event_entity_name`` parameter.

TODO - Specifying event serializer
