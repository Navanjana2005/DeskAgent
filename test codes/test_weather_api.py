import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather(city: str) -> dict | None:
    """
    Fetch current weather data for the given city.
    Returns a dictionary of weather details or None on failure.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("❌ OPENWEATHER_API_KEY is not set in the environment or .env file.")
        return None

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"   # Use 'imperial' for Fahrenheit
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"❌ City '{city}' not found. Please check the spelling.")
            return None
        elif response.status_code == 401:
            print("❌ Invalid API key. Please check your .env file.")
        else:
            print(f"❌ HTTP error occurred: {http_err}")
        return None

    except requests.exceptions.ConnectionError:
        print("❌ Network error. Please check your internet connection.")
        return None

    except requests.exceptions.Timeout:
        print("❌ Request timed out. Try again later.")
        return None


def display_weather(data: dict) -> None:
    """
    Parse and print weather data in a human-readable format.
    """
    city_name    = data["name"]
    country      = data["sys"]["country"]
    temperature  = data["main"]["temp"]
    feels_like   = data["main"]["feels_like"]
    humidity     = data["main"]["humidity"]
    description  = data["weather"][0]["description"].capitalize()
    wind_speed   = data["wind"]["speed"]

    print("\n" + "=" * 40)
    print(f"📍 Weather in {city_name}, {country}")
    print("=" * 40)
    print(f"🌡️  Temperature : {temperature}°C (Feels like {feels_like}°C)")
    print(f"💧 Humidity    : {humidity}%")
    print(f"🌬️  Wind Speed  : {wind_speed} m/s")
    print(f"🌤️  Condition   : {description}")
    print("=" * 40 + "\n")


if __name__ == "__main__":
    city = input("Enter city name: ").strip()
    if city:
        weather_data = get_weather(city)
        if weather_data:
            display_weather(weather_data)
    else:
        print("❌ City name cannot be empty.")