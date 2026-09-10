from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
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

@router.post("", response_model=PerfumeRead, status_code=status.HTTP_201_CREATED)
def create_perfume(
    data: PerfumeCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    statement = select(Perfume).where(Perfume.barcode == data.barcode)
    existing = session.exec(statement).first()

    if existing is None:
        perfume = Perfume.model_validate(data)
        session.add(perfume)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.exec(statement).one()
        else:
            session.refresh(perfume)
            return perfume

    response.status_code = status.HTTP_200_OK
    existing.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


@router.get("/{perfume_id}", response_model=PerfumeRead)
def get_perfume_by_id(perfume_id: int, session: Session = Depends(get_session)):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        raise HTTPException(status_code=404, detail="Perfume not found")
    return perfume


@router.patch("/{perfume_id}", response_model=PerfumeRead)
def patch_perfume_by_id(perfume_id : int, data: PerfumeUpdate, session: Session = Depends(get_session)):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        raise HTTPException(status_code=404, detail="Perfume not found")
    changes = data.model_dump(exclude_unset=True)
    perfume.sqlmodel_update(changes)
    session.add(perfume)
    session.commit()
    session.refresh(perfume)
    return perfume

@router.delete("/{perfume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_perfume_by_id(perfume_id: int, session: Session = Depends(get_session)):
    perfume = session.get(Perfume, perfume_id)
    if perfume is None:
        return
    session.delete(perfume)
    session.commit()
    