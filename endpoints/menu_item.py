from fastapi import APIRouter, HTTPException

from database.schemas import MenuItemCreate

router = APIRouter(prefix="/menu-item", tags=["menu-item"])


@router.post("/confirm-with-image")
async def confirm_menu_item_with_image(payload: MenuItemCreate):
    try:
        if not payload.name or not payload.name.strip():
            raise HTTPException(status_code=400, detail="Item name is required.")

        if not payload.preview_image_name:
            raise HTTPException(status_code=400, detail="preview_image_name is required.")

        candidate_item = payload.dict()
        preview_image_name = candidate_item.pop("preview_image_name", None)
        result = await confirm_candidate_item(candidate_item,preview_image_name)
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


import os
import re
import uuid
import base64
from io import BytesIO

import boto3
import httpx
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
MENU_API_BASE_URL = os.getenv("MENU_API_BASE_URL", "http://menu-backend.seasonedspoon:8002")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
s3_client = boto3.client("s3", region_name=AWS_REGION)


def _slugify(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "menu-item"


def build_image_prompt(candidate_item: dict) -> str:
    name = candidate_item.get("name", "menu item")
    description = candidate_item.get("description", "")
    return (
        f"Professional food photography of {name}. "
        f"{description} "
        "Restaurant menu photo, realistic, premium plating, clean background, "
        "soft lighting, highly appetizing, high detail, no text, no watermark."
    )


def generate_menu_item_image_bytes(candidate_item: dict) -> bytes:
    prompt = build_image_prompt(candidate_item)

    result = openai_client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
    )

    image_base64 = result.data[0].b64_json
    return base64.b64decode(image_base64)


def upload_image_bytes_to_s3(image_bytes: bytes, key: str) -> str:
    print(S3_BUCKET_NAME)
    print(key)
    print("SEESEE")
    s3_client.upload_fileobj(
        Fileobj=BytesIO(image_bytes),
        Bucket="seasonedspoonimages",
        Key=key,
        ExtraArgs={"ContentType": "image/png"},
    )
    return f"https://{"seasonedspoonimages"}.s3.{AWS_REGION}.amazonaws.com/{key}"


async def save_candidate_item_to_db(candidate_item: dict, token: str | None = None) -> dict:
    url = f"{MENU_API_BASE_URL}/api/menu-item/confirm"
    print("trying to save")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "name": candidate_item.get("name"),
        "description": candidate_item.get("description"),
        "price": candidate_item.get("price"),
        "categoryId": candidate_item.get("category_id"),
        "subcategoryId": candidate_item.get("subcategory_id"),
        "isChefRecommend": candidate_item.get("is_chef_recommend", False),
        "image_url": candidate_item.get("image_url"),
    }
    print("going to save")
    print(url)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

@router.post("/preview-image")
async def preview_candidate_item_image(candidate_item: dict) -> dict:
    image_bytes = generate_menu_item_image_bytes(candidate_item)

    preview_id = uuid.uuid4().hex
    preview_name = f"{_slugify(candidate_item.get('name', 'menu-item'))}-preview-{preview_id}.png"
    preview_key = f"public/previews/{preview_name}"

    preview_image_url = upload_image_bytes_to_s3(
        image_bytes=image_bytes,
        key=preview_key,
    )

    return {
        "message": "Preview generated. Confirm if you want to save this menu item.",
        "type": "candidate_preview",
        "preview_id": preview_id,
        "preview_image_url": preview_image_url,
        "preview_image_name": preview_name,
        "candidate_item": candidate_item,
    }


async def confirm_candidate_item(
    candidate_item: dict,
    preview_image_name: str,
    token: str | None = None
) -> dict:
    print("i am going")
    print(preview_image_name)
    # 🚀 Move image from previews → img
    final_image_url = await move_preview_to_img(preview_image_name)

    # Update payload with final image location
    candidate_item["image_url"] = final_image_url

    db_result = await save_candidate_item_to_db(candidate_item, token)

    return {
        "db_result": db_result,
        "message": "Menu item inserted successfully.",
        "item_id": (
            db_result.get("itemId")
            or db_result.get("item_id")
            or db_result.get("id")
        ),
        "name": db_result.get("name"),
        "image_url": final_image_url,
    }

async def move_preview_to_img(preview_image_name: str) -> str:
    source_key = f"public/previews/{preview_image_name}"
    destination_key = f"public/img/{preview_image_name}"

    # Copy
    s3_client.copy_object(
        Bucket=S3_BUCKET_NAME,
        CopySource={
            "Bucket": S3_BUCKET_NAME,
            "Key": source_key
        },
        Key=destination_key
    )

    # Delete original
    s3_client.delete_object(
        Bucket=S3_BUCKET_NAME,
        Key=source_key
    )

    # Return new URL
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{destination_key}"