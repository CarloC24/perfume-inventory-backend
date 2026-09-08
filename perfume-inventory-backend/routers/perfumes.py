from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select

from database import get_session
from models import Perfume, PerfumeCreate, PerfumeRead, PerfumeUpdate



router = APIRouter(prefix="/perfumes", tags=["perfumes"])

@router.get("", response_model=list[PerfumeRead])
def list_perfumes(
    session: Session = Depends(get_session)
):
    statement = select(Perfume)
    return session.exec(statement).all()

