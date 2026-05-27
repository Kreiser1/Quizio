import importlib
import pkgutil
from pathlib import Path
from fastapi import APIRouter
from schema import Configuration
import config

api_router = APIRouter(prefix='/api', tags=['API'])

@api_router.get('/', response_model=Configuration)
def configuration() -> Configuration:
    return Configuration(
        auth_cooldown=config.AUTH_COOLDOWN,
        auth_expiration=config.AUTH_EXPIRATION,
        token_expiration=config.TOKEN_EXPIRATION,
        image_size_limit=config.IMAGE_SIZE_LIMIT,
        quiz_size_limit=config.QUIZ_SIZE_LIMIT,
        frequency=config.FREQUENCY
    )

package_dir = Path(__file__).resolve().parent

for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
    module = importlib.import_module(f".{module_name}", package=__name__)
    if hasattr(module, "router"):
        sub_router = getattr(module, "router")
        if isinstance(sub_router, APIRouter):
            api_router.include_router(sub_router)
