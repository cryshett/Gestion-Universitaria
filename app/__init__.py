"""Paquete principal de la aplicación mb-system y re-exportación del servidor Flask para Gunicorn."""
import os
import sys
import importlib.util

_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_app_py = os.path.join(_root_dir, "app.py")

if os.path.exists(_app_py):
    if "app_root_server" in sys.modules:
        _mod = sys.modules["app_root_server"]
    else:
        spec = importlib.util.spec_from_file_location("app_root_server", _app_py)
        _mod = importlib.util.module_from_spec(spec)
        sys.modules["app_root_server"] = _mod
        spec.loader.exec_module(_mod)
    app = getattr(_mod, "app", None)
