from tauon import define_agent, define_tool, use_model, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Real implementation would call a weather API.
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> str:
    use_model("gpt-5.6-luna")
    use_tool(get_weather)
    return (
        "You are a weather assistant. "
        "When the user asks about the weather, call the get_weather tool with the city name."
    )
