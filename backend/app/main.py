from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers import auth, core, outreach, billing

app = FastAPI(
    title="Acreva HireFlow API",
    version="2.0.0",
    description="AI-assisted recruitment workflow API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "")
    allowed = settings.cors_origin_list or ["http://localhost:3000"]
    if origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        headers=_cors_headers(request),
        content={
            "detail": "Something went wrong. Please try again or contact support.",
            "support_email": settings.support_email,
            "error": str(exc),
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "product": "Acreva HireFlow"}


@app.get("/")
def root():
    return {"status": "ok", "product": "Acreva HireFlow", "docs": "/docs", "health": "/health"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(core.router, prefix="/api/v1")
app.include_router(outreach.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
