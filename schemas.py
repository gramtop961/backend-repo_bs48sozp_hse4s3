"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional

# Example schemas (you can keep or remove these if not needed):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Inventory tracking schema (this powers the inventory app)
class Item(BaseModel):
    """
    Inventory items schema
    Collection name: "item"
    """
    name: str = Field(..., description="Item name")
    sku: str = Field(..., description="Stock Keeping Unit")
    category: Optional[str] = Field(None, description="Category")
    location: Optional[str] = Field(None, description="Storage location")
    quantity: int = Field(0, ge=0, description="On-hand quantity")
    min_stock: Optional[int] = Field(0, ge=0, description="Reorder threshold")
    cost: Optional[float] = Field(0.0, ge=0, description="Unit cost")
    price: Optional[float] = Field(0.0, ge=0, description="Selling price")

# Add your own schemas here as needed.
