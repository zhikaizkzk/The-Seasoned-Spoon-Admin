from pydantic import BaseModel
from typing import Optional

class MenuItemCreate(BaseModel):
    category_id: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_chef_recommend: Optional[bool] = False
    name: str
    price: Optional[float] = None
    subcategory_id: Optional[int] = None
    preview_image_name: Optional[str] = None