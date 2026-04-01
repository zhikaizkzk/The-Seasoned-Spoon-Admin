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


def upload_image_bytes_to_s3(image_bytes: bytes, item_name: str) -> str:
    key = f"public/public/img/{_slugify(item_name)}-{uuid.uuid4().hex}.png"

    s3_client.upload_fileobj(
        Fileobj=BytesIO(image_bytes),
        Bucket="seasonedspoonimagesprod",
        Key=key,
        ExtraArgs={"ContentType": "image/png"},
    )

    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"


async def save_candidate_item_to_db(candidate_item: dict, token: str | None = None) -> dict:
    url = f"{MENU_API_BASE_URL}/api/menu-item/confirm"
    print(url)
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

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("can")
        print(response)
        return response.json()


async def confirm_candidate_item(candidate_item: dict, token: str | None = None) -> dict:
    image_bytes = generate_menu_item_image_bytes(candidate_item)

    image_url = upload_image_bytes_to_s3(
        image_bytes=image_bytes,
        item_name=candidate_item.get("name", "menu-item"),
    )

    candidate_item["image_url"] = image_url

    db_result = await save_candidate_item_to_db(candidate_item, token)
    print("db_result:", db_result)
    return {
        "db_result": db_result,
        "message": "Menu item inserted successfully.",
        "item_id": (
            db_result.get("itemId")
            or db_result.get("item_id")
            or db_result.get("id")
        ),
        "name": db_result.get("name"),
        "image_url": (
            db_result.get("imageUrl")
            or db_result.get("image_url")
            or image_url
        ),
    }