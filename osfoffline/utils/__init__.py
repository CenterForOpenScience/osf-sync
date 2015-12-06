import asyncio
import threading


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        key = (getattr(cls, 'thread_safe', False) and cls) or (threading.get_ident(), cls)
        if key not in cls._instances:
            cls._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[key]


def ensure_event_loop():
    """Ensure the existance of an eventloop
    Useful for contexts where get_event_loop() may raise an exception.
    Such as multithreaded applications

    :returns: The new event loop
    :rtype: BaseEventLoop
    """
    try:
        return asyncio.get_event_loop()
    except (AssertionError, RuntimeError):
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Note: No clever tricks are used here to dry up code
    # This avoids an infinite loop if settings the event loop ever fails
    return asyncio.get_event_loop()
