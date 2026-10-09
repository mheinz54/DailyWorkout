from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.server.database import check_database_connection

app = FastAPI(title="Daily Workout API", version="0.1.0")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness_check() -> dict[str, str]:
    try:
        check_database_connection()
    except (RuntimeError, SQLAlchemyError) as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ready", "database": "connected"}