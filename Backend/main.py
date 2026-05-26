import base64
import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()

app = FastAPI(title="NutriScan AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UIIngredientRow(BaseModel):
    name: str
    weight_grams: int = Field(ge=0)
    calories: int = Field(ge=0)


class NutriScanResponse(BaseModel):
    meal_title: str
    ingredients: List[UIIngredientRow] = Field(default_factory=list)
    total_calories: int = Field(ge=0)


ANALYSIS_PROMPT = """
You are an expert computer-vision nutrition assistant. Analyze the uploaded meal image and estimate visible foods only.

Return one raw JSON object with exactly this shape:
{
  "meal_title": "Meal Breakdown: short display name",
  "ingredients": [
    {"name": "ingredient name", "weight_grams": 100, "calories": 120}
  ],
  "total_calories": 120
}

Rules:
- Isolate every distinct visible food item or topping.
- Estimate realistic portion weights in grams.
- Use standard calorie baselines for the visible portion.
- If small local banana varieties such as Nano or Thihmway bananas are detected, estimate 50g-70g per fruit instead of a standard 120g banana.
- total_calories must be the exact sum of ingredient calories.
- Return only valid JSON. No markdown, no commentary.
""".strip()


DEMO_RESPONSE = NutriScanResponse(
    meal_title="Meal Breakdown: Sample Mixed Plate",
    ingredients=[
        UIIngredientRow(name="Steamed rice", weight_grams=150, calories=195),
        UIIngredientRow(name="Grilled chicken", weight_grams=120, calories=198),
        UIIngredientRow(name="Mixed vegetables", weight_grams=90, calories=45),
        UIIngredientRow(name="Light sauce", weight_grams=20, calories=30),
    ],
    total_calories=468,
)


@app.get("/api/health")
def health_check():
    openrouter_configured = bool(os.environ.get("OPENROUTER_API_KEY"))
    return {
        "ok": True,
        "openrouter_configured": openrouter_configured,
        "gemini_configured": openrouter_configured,
    }


@app.post("/api/scan", response_model=NutriScanResponse)
async def scan_meal_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return DEMO_RESPONSE

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [
            {
                "role": "system",
                "content": ANALYSIS_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this meal image and return the nutrition estimate as strict JSON.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file.content_type};base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 1200,
    }

    url = "https://openrouter.ai/api/v1/chat/completions"

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"OpenRouter request failed: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"OpenRouter API error: {response.text}")

    try:
        response_json = response.json()
        raw_text = response_json["choices"][0]["message"]["content"].strip()
        clean_json_string = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = NutriScanResponse.model_validate_json(clean_json_string)
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter returned an unexpected response: {exc}",
        ) from exc

    calculated_total = sum(item.calories for item in result.ingredients)
    if result.total_calories != calculated_total:
        result.total_calories = calculated_total

    return result
