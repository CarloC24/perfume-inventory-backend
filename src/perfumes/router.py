from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session

from src.database import get_session
from src.pagination import PaginationParams
from src.perfumes import service
from src.perfumes.constants import ROUTER_PREFIX, ROUTER_TAGS
from src.perfumes.dependencies import valid_perfume_id
from src.perfumes.models import Perfume
from src.perfumes.schemas import PerfumeCreate, PerfumeRead, PerfumeUpdate

router = APIRouter(prefix=ROUTER_PREFIX, tags=ROUTER_TAGS)


@router.get("", response_model=list[PerfumeRead])
def list_perfumes(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    return service.get_all(session, pagination)


@router.post("", response_model=PerfumeRead, status_code=status.HTTP_201_CREATED)
def create_perfume(
    data: PerfumeCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    perfume, created = service.upsert_by_barcode(session, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return perfume


@router.get("/{perfume_id}", response_model=PerfumeRead)
def get_perfume_by_id(perfume: Perfume = Depends(valid_perfume_id)):
    return perfume


@router.patch("/{perfume_id}", response_model=PerfumeRead)
def patch_perfume_by_id(
    data: PerfumeUpdate,
    perfume: Perfume = Depends(valid_perfume_id),
    session: Session = Depends(get_session),
):
    return service.update(session, perfume, data)


@router.delete("/{perfume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_perfume_by_id(perfume_id: int, session: Session = Depends(get_session)):
    # A missing row is not an error: DELETE is idempotent, so this answers 204
    # whether or not there was anything to remove.
    perfume = service.get_by_id(session, perfume_id)
    if perfume is None:
        return
    service.delete(session, perfume)
