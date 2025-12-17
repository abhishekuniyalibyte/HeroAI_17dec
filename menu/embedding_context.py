# menu/embedding_context.py
from contextlib import contextmanager
from contextvars import ContextVar

# Per-thread / per-request flag (global bool se safe)
_embeddings_signals_disabled: ContextVar[bool] = ContextVar(
    "embeddings_signals_disabled",
    default=False,
)


def are_embedding_signals_disabled() -> bool:
    """
    Check karo ki abhi embeddings-related signals ko ignore karna hai ya nahi.
    """
    return _embeddings_signals_disabled.get()


@contextmanager
def suspend_embedding_signals():
    """
    Isko `with` ke andar use karo jab bulk rebuild kar rahe ho, e.g.

    with suspend_embedding_signals():
        rebuild_menu_from_json(...)

    Is block ke andar jitne bhi MenuItem save/delete honge,
    unke signals early-return kar denge (no Celery spam).
    """
    token = _embeddings_signals_disabled.set(True)
    try:
        yield
    finally:
        # Always reset (exception ho tab bhi)
        _embeddings_signals_disabled.reset(token)
