#!/usr/bin/python3
import sys
import os

# Añadimos la ruta actual al sistema para que encuentre server.py
sys.path.insert(0, os.path.dirname(__file__))

from a2wsgi import ASGIMiddleware
from server import app

# Esto adapta FastAPI (ASGI) al formato WSGI/CGI que entiende IONOS
compiler = ASGIMiddleware(app)

if __name__ == '__main__':
    from wsgiref.handlers import CGIHandler
    CGIHandler().run(compiler)