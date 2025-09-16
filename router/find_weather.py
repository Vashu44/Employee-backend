import httpx
from fastapi import APIRouter, Query, HTTPException
import asyncio

router = APIRouter(
    prefix="/api" # Prefix yahan add karein
)


def interpret_weather_code(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in [1, 2, 3]:
        return "Cloudy"
    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "Rain"
    if code in [71, 73, 75, 85, 86]:
        return "Snow"
    return "N/A"

@router.get("/weather")
async def find_weather(lat: float = Query(...), lon: float = Query(...)):
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
    geo_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"

    async with httpx.AsyncClient() as client:
        try:
          
            weather_task = client.get(weather_url)
            # Nominatim API ke liye User-Agent header zaroori hai
            geo_task = client.get(geo_url, headers={"User-Agent": "MyWeatherApp/1.0"})
            
            weather_resp, geo_resp = await asyncio.gather(weather_task, geo_task)

            
            weather_resp.raise_for_status()
            geo_resp.raise_for_status()

            weather_data = weather_resp.json()
            geo_data = geo_resp.json()

            
            temp = weather_data.get("current_weather", {}).get("temperature")
            weather_code = weather_data.get("current_weather", {}).get("weathercode")
            
            address = geo_data.get("address", {})
            city = address.get("city") or address.get("town") or address.get("village")

            return {
                "temp": round(temp) if temp is not None else None,
                "condition": interpret_weather_code(weather_code) if weather_code is not None else "N/A",
                "city": city or "Unknown Location"
            }

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch data from an external service.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")