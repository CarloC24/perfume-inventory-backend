from fastapi import FastAPI
from routers import perfumes
from contextlib import asynccontextmanager
from database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Perfume Inventory", lifespan=lifespan)

app.include_router(perfumes.router)

@app.get("/hello")
def read_root():
    return {"message": "Hello World"}
