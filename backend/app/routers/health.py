from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "udaan-api",
        "version": "0.1.0",
    }
