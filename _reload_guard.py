"""
Process-global bookkeeping for detecting local modules that changed on disk.

Streamlit Cloud can keep a warm Python process across a git deploy. The
entry script and page scripts are re-read from disk on every rerun, but
modules already in ``sys.modules`` stay at their old version — so new page
code ends up calling into old helper code. That mismatch has surfaced as
``ImportError: cannot import name ...`` and ``AttributeError: ... has no
attribute ...`` right after several deploys, each needing a manual
"Reboot app".

This module is deliberately tiny and never reloaded itself, so ``MTIMES``
survives for the lifetime of the process and gives ``reload_changed()`` a
stable place to remember what it has already seen.
"""

import importlib
import os
import sys

# module name -> last-seen source mtime
MTIMES: dict[str, float] = {}

# Reload order matters: a module must come after anything it imports names
# from, so it re-executes its `from x import y` against the fresh version.
LOCAL_MODULES = (
    "app_common",
    "news_service",
    "sheet_store",
    "settings_dialog",
)


def reload_changed(module_names=LOCAL_MODULES) -> list[str]:
    """Reload any of `module_names` whose source file changed since the last
    call. Returns the names that were reloaded.

    The first call only records timestamps (those modules were just imported,
    so they're already current). Normal reruns find nothing changed and cost
    a handful of stat() calls, which keeps `st.cache_data` caches intact.
    """
    reloaded: list[str] = []
    # Once something reloads, everything after it in dependency order is
    # reloaded too: a module that did `from app_common import X` still holds
    # the old X until it re-executes, which would leave the two disagreeing.
    cascade = False

    for name in module_names:
        module = sys.modules.get(name)
        if module is None:
            continue

        path = getattr(module, "__file__", None)
        if not path:
            continue

        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue

        previous = MTIMES.get(name)
        changed = previous is not None and previous != mtime

        if changed or cascade:
            try:
                importlib.reload(module)
                reloaded.append(name)
                cascade = True
            except Exception:
                # Never let a reload problem take the app down; the worst
                # case is the pre-existing stale-module behavior.
                pass

        MTIMES[name] = mtime

    return reloaded
