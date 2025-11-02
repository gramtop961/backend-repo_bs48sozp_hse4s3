import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Item

app = FastAPI(title="Inventory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------
# Utility functions
# -----------------

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# -----------------
# Health/Test routes
# -----------------
@app.get("/")
def read_root():
    return {"message": "Inventory API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# --------------
# Inventory API
# --------------

class ItemCreate(Item):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    min_stock: Optional[int] = Field(None, ge=0)
    cost: Optional[float] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)

class AdjustStock(BaseModel):
    delta: int = Field(..., description="Positive to add, negative to remove")

@app.get("/items")
def list_items(q: Optional[str] = Query(None, description="Search by name or SKU"), category: Optional[str] = None) -> List[Dict[str, Any]]:
    filter_query: Dict[str, Any] = {}
    if q:
        # simple OR condition on name and sku using regex
        filter_query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"sku": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filter_query["category"] = category

    docs = get_documents("item", filter_query)
    return [serialize_doc(d) for d in docs]

@app.post("/items", status_code=201)
def create_item(item: ItemCreate) -> Dict[str, Any]:
    # enforce unique SKU within collection
    if db.item.find_one({"sku": item.sku}):
        raise HTTPException(status_code=400, detail="SKU already exists")

    inserted_id = create_document("item", item)
    doc = db.item.find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)

@app.put("/items/{item_id}")
def update_item(item_id: str, data: ItemUpdate) -> Dict[str, Any]:
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item id")

    payload = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    # prevent SKU collision
    if "sku" in payload:
        existing = db.item.find_one({"sku": payload["sku"], "_id": {"$ne": oid}})
        if existing:
            raise HTTPException(status_code=400, detail="SKU already in use by another item")

    result = db.item.update_one({"_id": oid}, {"$set": payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    doc = db.item.find_one({"_id": oid})
    return serialize_doc(doc)

@app.post("/items/{item_id}/adjust")
def adjust_stock(item_id: str, body: AdjustStock) -> Dict[str, Any]:
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item id")

    doc = db.item.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")

    new_qty = max(0, int(doc.get("quantity", 0)) + body.delta)
    db.item.update_one({"_id": oid}, {"$set": {"quantity": new_qty}})
    updated = db.item.find_one({"_id": oid})
    return serialize_doc(updated)

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid item id")

    result = db.item.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}

@app.get("/items/stats")
def inventory_stats() -> Dict[str, Any]:
    items = list(db.item.find())
    total_skus = len(items)
    total_units = sum(int(i.get("quantity", 0)) for i in items)
    low_stock = sum(1 for i in items if int(i.get("min_stock", 0) or 0) > int(i.get("quantity", 0) or 0))
    return {
        "total_skus": total_skus,
        "total_units": total_units,
        "low_stock": low_stock,
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
