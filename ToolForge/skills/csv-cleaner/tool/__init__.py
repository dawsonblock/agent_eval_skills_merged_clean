try:
    from .main import run
except Exception:
    def run(*args, **kwargs):
        raise NotImplementedError("run is not implemented in tool/main.py")

__all__ = ["run"]
