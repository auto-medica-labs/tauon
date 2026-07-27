# This example uses Tauon's built-in model catalog and environment variables
# for API keys. It does not load saved Tau agent credentials.
from tauon import define_agent, define_tool, use_model, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Real implementation would call a weather API.
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> str:
    # export OPENROUTER_API_KEY=sk-... before use
    # use_model("openrouter/qwen/qwen3.5-9b") # or
    # export OPENAI_API_KEY=sk...
    use_model("gpt-5.6-luna")
    use_tool(get_weather)
    return (
        "You are a weather assistant. "
        "When the user asks about the weather, call the get_weather tool with the city name."
    )
