# tools/weather.py
import requests

def get_weather(city: str) -> str:
    """
    Get current weather using wttr.in — completely free, no API key needed.
    Returns a clean string the LLM can read and summarize naturally.
    """
    try:
        # wttr.in is a free weather service with a clean JSON API
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        
        city_name = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        temp_c = current["temp_C"]
        feels_like = current["FeelsLikeC"]
        humidity = current["humidity"]
        description = current["weatherDesc"][0]["value"]
        wind_kmph = current["windspeedKmph"]
        
        return (
            f"Weather in {city_name}, {country}: {description}. "
            f"Temperature: {temp_c}°C (feels like {feels_like}°C). "
            f"Humidity: {humidity}%. Wind: {wind_kmph} km/h."
        )
    
    except Exception as e:
        return f"Couldn't get weather for {city}: {str(e)}"