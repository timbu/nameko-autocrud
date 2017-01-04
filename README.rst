nameko-autocrud
=================

-  An experimental (slightly magical) utility to automatically add CRUD RPC and (possibly HTTP) entrypoints to nameko microservices.
-  Based on Sqlalchemy models.
-  Aim is to reduce the amount of code required.
-  (Will) use sqlalchemy-filters. 
-  (probably) requires nameko-sqlalchemy.

Usage
-----

.. code-block:: python

    from nameko_autocrud import AutoCrud
    from nameko_sqlalchemy import DatabaseSession


    class MemberAutoCrud(AutoCrud):
        crud_model_cls = models.Member


    class PaymentAutoCrud(AutoCrud):
        crud_model_cls = models.Payment


    class MyService(MemberAutoCrud, PaymentAutoCrud):
    
        name = 'my_service'
        session = DatabaseSession(models.Base)
        
        @rpc
        def my_entrypoint(self, value):
            return value + 1

OR...

.. code-block:: python

    from nameko_autocrud import autocrud_factory
    from nameko_sqlalchemy import DatabaseSession


    MyAutoCrud = autocrud_factory({
        'crud_models': [
            {'model_cls': models.Member},
            {'model_cls': models.Payment},
        ]
    })


    class MyService(MyAutoCrud):
    
        name = 'my_service'
        session = DatabaseSession(models.Base)
        
        @rpc
        def my_entrypoint(self, value):
            return value + 1
            
      
This will automatically make the following additional RPC entrypoints available

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
    
