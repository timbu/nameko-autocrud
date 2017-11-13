nameko-autocrud
=================

-  An experimental (slightly magical) dependency to automatically add CRUD RPC (and possibly later HTTP) entrypoints to nameko microservices.
-  Based on Sqlalchemy models.
-  Aim is to reduce the amount of code required to implement common methods.
-  Uses sqlalchemy-filters.
-  Works in conjunction with sqlalchemy dependency providers such as nameko-sqlalchemy.
-  Each dependency also can be used in other methods to get/manipulate model instances.
-  Customisable components.

Usage
-----

.. code-block:: python

    from nameko_sqlalchemy import DatabaseSession
    from nameko_autocrud import AutoCrudProvider

    class MyService:

        name = 'my_service'
        session = DatabaseSession(models.Base)
        
        member_auto_crud = AutoCrud(session, model_cls=models.Member)
        payment_auto_crud = AutoCrud(session, model_cls=models.Payment)

        @rpc
        def my_entrypoint(self, value):
            return value + 1


This will automatically make the following additional RPC entrypoints available:

.. code-block:: python

    get_member(self, id_)
    list_members(self, filters=None, offset=None, limit=None)
    page_members(self, page_size, page_num, filters=None)    
    count_members(self, filters=None)
    update_member(self, id_, data)
    create_member(self, data)
    delete_member(self, id_)
    get_payment(self, id_)
    list_payments(self, filters=None, offset=None, limit=None)
    page_payments(self, page_size, page_num, filters=None)
    count_payments(self, filters=None)
    update_payment(self, id_, data)
    create_payment(self, data)
    delete_payment(self, id_)

The dependencies themselves can be used to manipulate sqlalchemy objects within other code E.g.

.. code-block:: python

    @rpc
    def copy_member_name(self, from_id, to_id):
        member = self.member_auto_crud.get(from_id)
        self.member_auto_crud.update(to_id, {'name': member.name})




