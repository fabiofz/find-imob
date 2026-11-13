"""Keep independent collection steps running without hiding partial failures."""
from contextlib import contextmanager
from contextvars import ContextVar
import traceback

from utils.funcs import registrar_erro_coleta

_active_failures = ContextVar('collection_failures', default=None)


@contextmanager
def collect_errors(failures):
    token = _active_failures.set(failures)
    try:
        yield
    finally:
        _active_failures.reset(token)


@contextmanager
def continue_on_error(label, failures=None):
    try:
        yield
    except Exception as error:
        # KeyboardInterrupt and SystemExit deliberately remain interruptible.
        print(f'[COLETA_PARCIAL] {label}: {type(error).__name__}: {error}. Continuando.', flush=True)
        target = failures if failures is not None else _active_failures.get()
        if target is not None:
            target.append((label, error))
        else:
            try:
                registrar_erro_coleta(label, traceback.format_exc(limit=8))
            except Exception as log_error:
                print(f'[LOG] Não foi possível registrar a falha: {log_error}', flush=True)
