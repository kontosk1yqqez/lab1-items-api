from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ItemModel

app = FastAPI(
    title="Items API",
    description="Простий REST API для керування списком товарів (CRUD). Дані зберігаються в PostgreSQL.",
    version="2.0.0",
)


class ItemIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Ноутбук"])
    description: str | None = Field(None, examples=["16 ГБ RAM, SSD 512 ГБ"])
    price: float = Field(..., ge=0, examples=[25999.0])


class Item(ItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


def get_or_404(session: Session, item_id: int) -> ItemModel:
    item = session.get(ItemModel, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.get("/healthz", tags=["service"])
def healthz(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/items", response_model=list[Item], tags=["items"])
def list_items(session: Session = Depends(get_session)):
    return session.scalars(select(ItemModel).order_by(ItemModel.id)).all()


@app.get("/api/items/{item_id}", response_model=Item, tags=["items"])
def get_item(item_id: int, session: Session = Depends(get_session)):
    return get_or_404(session, item_id)


@app.post("/api/items", response_model=Item, status_code=status.HTTP_201_CREATED, tags=["items"])
def create_item(data: ItemIn, session: Session = Depends(get_session)):
    item = ItemModel(**data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.put("/api/items/{item_id}", response_model=Item, tags=["items"])
def update_item(item_id: int, data: ItemIn, session: Session = Depends(get_session)):
    item = get_or_404(session, item_id)
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["items"])
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = get_or_404(session, item_id)
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
