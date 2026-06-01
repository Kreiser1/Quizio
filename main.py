from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, security, schema, config, database as db
from exceptions import *
import mimetypes

with db.connect() as session:
    if not session.execute(db.select(db.User)).first():
        if security.register(session, schema.UserRegistration(
            username=config.ADMIN_USERNAME,
            password=config.ADMIN_PASSWORD
        )):
            security.set_role(session, schema.UserRoleUpdate(username=config.ADMIN_USERNAME, role='administrator'))

import config
from api import api_router

app = FastAPI(title='Quizio', description='Quizio API')

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = FastAPI.openapi(app)
    
    openapi_schema['components']['securitySchemes'] = {
        'AccessCookie': {
            'type': 'apiKey',
            'in': 'cookie',
            'name': security.ACCESS_COOKIE,
            'description': 'Токен доступа в куках. Устанавливается автоматически в /login.'
        },
        'RefreshCookie': {
            'type': 'apiKey',
            'in': 'cookie',
            'name': security.REFRESH_COOKIE,
            'description': 'Токен обновления в куках. Устанавливается автоматически в /login.'
        }
    }
    
    openapi_schema['security'] = [
        {'AccessCookie': [], 'RefreshCookie': []}
    ]

    openapi_schema['paths']['/api/rooms/{room_token}/stream'] = {
        'get': {
            'description': 'WebSocket для просмотра комнаты в реальном времени.',
            'tags': ['Комнаты'],
            'parameters': [
                {
                    'name': 'room_token',
                    'in': 'path',
                    'required': True,
                    'schema': {
                        'type': 'string'
                    }
                }
            ]
        }
    }
    
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    # allow_origin_regex=r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$',
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)

FRONTEND = 'frontend'

@app.get('/{route:path}')
def frontend(route: str):
    if route.lower().startswith('api/'):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
        
    if not route and os.path.exists(FRONTEND + '/index.html'):
        return FileResponse(FRONTEND + '/index.html')
        
    path = os.path.join(FRONTEND, route)

    if os.path.exists(path) and os.path.isfile(path):
        media_type, _ = mimetypes.guess_type(path)
        return FileResponse(path, media_type=media_type)
    
    return FileResponse(FRONTEND + '/index.html') if os.path.exists(FRONTEND + '/index.html') else Response(status_code=status.HTTP_404_NOT_FOUND)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=80, reload=True)