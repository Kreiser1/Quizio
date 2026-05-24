from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import security, schema, config, database as db

with db.connect() as session:
    if security.register(session, schema.UserRegistration(
        username=config.ADMIN_USERNAME,
        password=config.ADMIN_PASSWORD
    )):
        security.update_role(session, schema.UserRoleUpdate(username=config.ADMIN_USERNAME, role='administrator'))

import config
from api import api_router

app = FastAPI(debug=config.DEBUG, title='Quizio', description='Quizio API')

# Переопределяем генерацию схемы OpenAPI, чтобы Swagger знал про куки
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = FastAPI.openapi(app)
    
    openapi_schema["components"]["securitySchemes"] = {
        "AccessCookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": security.ACCESS_COOKIE,
            "description": "Токен доступа в куках. Устанавливается автоматически в /login."
        },
        "RefreshCookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": security.REFRESH_COOKIE,
            "description": "Токен обновления в куках. Устанавливается автоматически в /login."
        }
    }
    
    openapi_schema["security"] = [
        {"AccessCookie": [], "RefreshCookie": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

origins = [
    "http://localhost:3000",
    "https://quizio.com" # Домен
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)