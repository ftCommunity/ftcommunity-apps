"""
Like :mod:`telepot.delegate`, this module has a bunch of seeder factories
and delegator factories.

.. autofunction:: per_chat_id
.. autofunction:: per_chat_id_in
.. autofunction:: per_chat_id_except
.. autofunction:: per_from_id
.. autofunction:: per_from_id_in
.. autofunction:: per_from_id_except
.. autofunction:: per_inline_from_id
.. autofunction:: per_inline_from_id_in
.. autofunction:: per_inline_from_id_except
.. autofunction:: per_application
.. autofunction:: per_message
"""

import asyncio
import traceback
from .. import exception
from . import helper

# Mirror traditional version to avoid having to import one more module
from ..delegate import (
    per_chat_id, per_chat_id_in, per_chat_id_except,
    per_from_id, per_from_id_in, per_from_id_except,
    per_inline_from_id, per_inline_from_id_in, per_inline_from_id_except,
    per_application, per_message
)

def _ensure_coroutine_function(fn):
    return fn if asyncio.iscoroutinefunction(fn) else asyncio.coroutine(fn)

def call(corofunc, *args, **kwargs):
    """
    :return:
        a delegator function that returns a coroutine object by calling
        ``corofunc(seed_tuple, *args, **kwargs)``.
    """
    corofunc = _ensure_coroutine_function(corofunc)
    def f(seed_tuple):
        return corofunc(seed_tuple, *args, **kwargs)
    return f

def create_run(cls, *args, **kwargs):
    """
    :return:
        a delegator function that calls the ``cls`` constructor whose arguments being
        a seed tuple followed by supplied ``*args`` and ``**kwargs``, then returns
        a coroutine object by calling the object's ``run`` method, which should be
        a coroutine function.
    """
    def f(seed_tuple):
        j = cls(seed_tuple, *args, **kwargs)
        return _ensure_coroutine_function(j.run)()
    return f

def create_open(cls, *args, **kwargs):
    """
    :return:
        a delegator function that calls the ``cls`` constructor whose arguments being
        a seed tuple followed by supplied ``*args`` and ``**kwargs``, then returns
        a looping coroutine object that uses the object's ``listener`` to wait for
        messages and invokes instance method ``open``, ``on_message``, ``on_timeout``,
        and ``on_close`` accordingly.
    """
    def f(seed_tuple):
        j = cls(seed_tuple, *args, **kwargs)

        async def wait_loop():
            bot, msg, seed = seed_tuple
            try:
                handled = await helper._yell(j.open, msg, seed)
                if not handled:
                    await helper._yell(j.on_message, msg)

                while 1:
                    try:
                        msg = await j.listener.wait()
                        await helper._yell(j.on_message, msg)
                    except exception.IdleTerminate:
                        raise
                    except exception.WaitTooLong as e:
                        await helper._yell(j.on_timeout, e)

            # These exceptions are "normal" exits.
            except (exception.IdleTerminate, exception.StopListening) as e:
                await helper._yell(j.on_close, e)

            # Any other exceptions are accidents. **Print it out.**
            # This is to prevent swallowing exceptions in the case that on_close()
            # gets overridden but fails to account for unexpected exceptions.
            except Exception as e:
                traceback.print_exc()
                await helper._yell(j.on_close, e)

        return wait_loop()
    return f
