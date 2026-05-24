import asyncio
import inspect


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "asyncio: mark a test as asyncio-driven without requiring pytest-asyncio",
    )


def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        signature = inspect.signature(test_func)
        accepted_args = {
            name: value
            for name, value in pyfuncitem.funcargs.items()
            if name in signature.parameters
        }
        asyncio.run(test_func(**accepted_args))
        return True
    return None