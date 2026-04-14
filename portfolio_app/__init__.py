"""Portfolio application package."""

__all__ = ["app", "create_app"]


def __getattr__(name: str):
    if name == "app":
        from .web import app

        return app
    if name == "create_app":
        from .web import create_app

        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
