from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .database import init_db
from .services.cache_service import CacheService
from .services.llm_gateway import LLMGateway


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])
    app.include_router(router)

    # Initialize synchronously so the service is ready before the first request,
    # including under simple ASGI servers and TestClient-based smoke tests.
    init_db()
    app.state.gateway = LLMGateway(settings, CacheService(settings.litellm_cache))

    return app


app = create_app()

