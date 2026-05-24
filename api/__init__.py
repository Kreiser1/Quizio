import importlib
import pkgutil
from pathlib import Path
from fastapi import APIRouter

api_router = APIRouter(prefix='/api')

package_dir = Path(__file__).resolve().parent

for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
    module = importlib.import_module(f".{module_name}", package=__name__)
    if hasattr(module, "router"):
        sub_router = getattr(module, "router")
        if isinstance(sub_router, APIRouter):
            api_router.include_router(sub_router)
