from fastapi import APIRouter, HTTPException

from endpoints.menu_item_confirm_service import confirm_candidate_item
from database.schemas import MenuItemCreate

router = APIRouter(prefix="/menu-item", tags=["menu-item"])


@router.post("/confirm-with-image")
async def confirm_menu_item_with_image(payload: MenuItemCreate):
    try:
        if not payload.name or not payload.name.strip():
            raise HTTPException(status_code=400, detail="Item name is required.")

        candidate_item = payload.dict()

        result = await confirm_candidate_item(candidate_item)
        print(result)
        print("look at result")
        return {
            "db_result": result.get("db_result"),
            "message": result.get("message", "Menu item inserted successfully."),
            "item_id": result.get("item_id"),
            "name": result.get("name"),
            "image_url": result.get("image_url"),
        }

    except Exception as e:
        print(f"Error in confirm-with-image API: {e}")
        raise HTTPException(status_code=500, detail=str(e))