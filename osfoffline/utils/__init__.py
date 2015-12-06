import threading


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        key = (getattr(cls, 'thread_safe', False) and cls) or (threading.get_ident(), cls)
        print(key)
        if key not in Singleton._instances:
            Singleton._instances[key] = super(Singleton, cls).__call__(*args, **kwargs)
        return Singleton._instances[key]
