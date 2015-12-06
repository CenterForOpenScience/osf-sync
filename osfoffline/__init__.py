import asyncio

__version__ = '0.0.1'

if not hasattr(asyncio, 'ensure_future'):
    asyncio.ensure_future = asyncio.async
