import httpx
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/weather")
async def find_weather(lat: float = Query(...), lon: float = Query(...)):
    async with httpx.AsyncClient() as client:
        weather_resp = await client.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        )
        geo_resp = await client.get(
            f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        )
        return {
            "weather": weather_resp.json(),
            "geo": geo_resp.json()
        }