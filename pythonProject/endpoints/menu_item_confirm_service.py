import os
import re
import uuid
import base64
from io import BytesIO

import boto3
import httpx
from openai import OpenAI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.model import MenuItem
from database.schemas import MenuItemCreate

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
MENU_API_BASE_URL = os.getenv("MENU_API_BASE_URL", "http://127.0.0.1:8007")

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


def upload_image_bytes_to_s3(image_bytes: bytes, item_name: str) -> str:
    key = f"public/public/img/{_slugify(item_name)}-{uuid.uuid4().hex}.png"

    s3_client.upload_fileobj(
        Fileobj=BytesIO(image_bytes),
        Bucket='seasonedspoonimagesprod',
        Key=key,
        ExtraArgs={"ContentType": "image/png"},
    )

    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"


async def save_candidate_item_to_db(candidate_item: dict, token: str | None = None) -> dict:
    url = f"{MENU_API_BASE_URL}/menu-item/confirm"

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "name": candidate_item.get("name"),
        "description": candidate_item.get("description"),
        "price": candidate_item.get("price"),
        "category_id": candidate_item.get("category_id"),
        "subcategory_id": candidate_item.get("subcategory_id"),
        "is_chef_recommend": candidate_item.get("is_chef_recommend", False),
        "image_url": candidate_item.get("image_url"),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()




async def confirm_candidate_item(candidate_item: dict, db: Session) -> dict:
    # 1. Generate image
    image_bytes = generate_menu_item_image_bytes(candidate_item)

    # 2. Upload to S3
    image_url = upload_image_bytes_to_s3(
        image_bytes=image_bytes,
        item_name=candidate_item.get("name", "menu-item"),
    )

    candidate_item["image_url"] = image_url

    # 3. Insert into DB (DIRECTLY, not via API)
    new_item = MenuItem(
        category_id=candidate_item.get("category_id"),
        description=candidate_item.get("description"),
        image_url=image_url,
        is_chef_recommend=1 if candidate_item.get("is_chef_recommend") else 0,
        name=candidate_item.get("name").strip(),
        price=candidate_item.get("price"),
        subcategory_id=candidate_item.get("subcategory_id"),
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "item_id": new_item.item_id,
        "name": new_item.name,
        "image_url": image_url,
    }