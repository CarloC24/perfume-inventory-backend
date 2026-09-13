from contextlib import asynccontextmanager
from logging.config import fileConfig
from pathlib import Path

from fastapi import FastAPI

from src.config import settings
from src.database import create_db_and_tables
from src.perfumes.router import router as perfumes_router

if Path(settings.LOGGING_CONFIG_FILE).is_file():
    fileConfig(settings.LOGGING_CONFIG_FILE, disable_existing_loggers=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title=settings.APP_TITLE, lifespan=lifespan)

app.include_router(perfumes_router)


@app.get("/hello")
def read_root():
    return {"message": "Hello World"}
