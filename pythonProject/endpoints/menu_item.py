from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from endpoints.menu_item_confirm_service import confirm_candidate_item
from models.model import MenuItem
from database.schemas import MenuItemCreate

router = APIRouter(prefix="/menu-item", tags=["menu-item"])

@router.post("/confirm")
def confirm_menu_item(payload: MenuItemCreate, db: Session = Depends(get_db)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Item name is required.")

    new_item = MenuItem(
        category_id=payload.category_id,
        description=payload.description,
        image_url=payload.image_url,
        is_chef_recommend=1 if payload.is_chef_recommend else 0,
        name=payload.name.strip(),
        price=payload.price,
        subcategory_id=payload.subcategory_id
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Menu item inserted successfully.",
        "item_id": new_item.item_id,
        "name": new_item.name
    }

@router.post("/confirm-with-image")
async def confirm_menu_item_with_image(
    payload: MenuItemCreate,
    db: Session = Depends(get_db)
):
    try:
        if not payload.name or not payload.name.strip():
            raise HTTPException(status_code=400, detail="Item name is required.")

        # Convert payload to dict (important)
        candidate_item = payload.dict()

        # Call your service (OpenAI + S3 + DB)
        result = await confirm_candidate_item(candidate_item,db)

        return {
            "message": "Menu item inserted successfully.",
            "item_id": result.get("item_id"),
            "name": result.get("name"),
            "image_url": result.get("image_url"),
        }

    except Exception as e:
        print(f"Error in confirm-with-image API: {e}")
        raise HTTPException(status_code=500, detail=str(e))