from contextlib import asynccontextmanager
from logging.config import fileConfig
from pathlib import Path

from fastapi import FastAPI

from src.config import settings
from src.perfumes.router import router as perfumes_router

if Path(settings.LOGGING_CONFIG_FILE).is_file():
    fileConfig(settings.LOGGING_CONFIG_FILE, disable_existing_loggers=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown work.

    Deliberately does not create tables. Alembic owns the schema, and a second
    thing creating it means the two disagree: create_all() builds the tables
    without stamping alembic_version, so the next `alembic upgrade head` finds
    a table it is about to create and fails with "table perfume already
    exists". Run migrations before starting the app.
    """
    yield


app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(perfumes_router)


@app.get("/hello")
def read_root():
    return {"message": "Hello World"}
