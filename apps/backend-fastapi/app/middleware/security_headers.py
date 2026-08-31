from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Cabeceras de seguridad HTTP estándar aplicadas a todas las respuestas.
# No se incluye Strict-Transport-Security (HSTS) porque el entorno de
# desarrollo corre sobre HTTP; agregarla cuando haya HTTPS/TLS por delante.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
