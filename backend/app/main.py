from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers.families import router as families_router
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Udaan API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "X-Member-Token"],
        expose_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " -> ".join(str(loc_part) for loc_part in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            messages.append(f"{loc}: {msg}" if loc else msg)
        formatted_message = "; ".join(messages) if messages else "Validation failed"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": formatted_message,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            code = exc.detail["code"]
            message = exc.detail["message"]
        elif exc.status_code == 404:
            code = "not_found"
            message = str(exc.detail) if exc.detail != "Not Found" else "Resource not found"
        else:
            code = f"http_{exc.status_code}"
            message = str(exc.detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An internal server error occurred.",
                }
            },
        )

    app.include_router(health_router)
    app.include_router(families_router)

    return app


app = create_app()
