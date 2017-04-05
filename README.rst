nameko-autocrud
=================

-  An experimental (slightly magical) dependency to automatically add CRUD RPC and (possibly HTTP) entrypoints to nameko microservices.
-  Based on Sqlalchemy models.
-  Aim is to reduce the amount of code required to implement common methods.
-  (Will) use sqlalchemy-filters.
-  (probably) requires nameko-sqlalchemy.

-  Should make the dependency act like a `storage` so it can be used in other methods to get/create model instances
-  The dependency should extend DatabaseSession so it manages the session itself.

Usage
-----

.. code-block:: python

    from nameko_autocrud import AutoCrudProvider
    from nameko_sqlalchemy import DatabaseSession


    class MyService:

        name = 'my_service'
        session = DatabaseSession(models.Base)
        member_auto_crud = AutoCrudProvider(models.Member)
        payment_auto_crud = AutoCrudProvider(models.Payment)

        @rpc
        def my_entrypoint(self, value):
            return value + 1


This will automatically make the following additional RPC entrypoints available:

.. code-block:: python

    get_member(self, id_)
    list_members(self, filters=None)
    update_member(self, id_, data)
    create_member(self, data)
    delete_member(self, id_)
    get_payment(self, id_)
    list_payments(self, filters=None)
    update_payment(self, id_, data)
    create_payment(self, data)
    delete_payment(self, id_)

