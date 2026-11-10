from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="Items API",
    description="Простий REST API для керування списком товарів (CRUD).",
    version="1.0.0",
)


class ItemIn(BaseModel):
    name: str = Field(..., min_length=1, examples=["Ноутбук"])
    description: str | None = Field(None, examples=["16 ГБ RAM, SSD 512 ГБ"])
    price: float = Field(..., ge=0, examples=[25999.0])


class Item(ItemIn):
    id: int


items: dict[int, Item] = {}
next_id = 1


def reset_storage():
    global next_id
    items.clear()
    next_id = 1


@app.get("/api/items", response_model=list[Item], tags=["items"])
def list_items():
    return list(items.values())


@app.get("/api/items/{item_id}", response_model=Item, tags=["items"])
def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return items[item_id]


@app.post("/api/items", response_model=Item, status_code=status.HTTP_201_CREATED, tags=["items"])
def create_item(data: ItemIn):
    global next_id
    item = Item(id=next_id, **data.model_dump())
    items[next_id] = item
    next_id += 1
    return item


@app.put("/api/items/{item_id}", response_model=Item, tags=["items"])
def update_item(item_id: int, data: ItemIn):
    if item_id not in items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    item = Item(id=item_id, **data.model_dump())
    items[item_id] = item
    return item


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["items"])
def delete_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    del items[item_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
