# Tauon

A minimal Python agent framework built on `tau-ai`.

## Quick start

```python
from tauon import define_agent, define_tool, use_model, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> str:
    use_model("openai/gpt-4.1-mini")
    use_tool(get_weather)
    return "You are a weather assistant."
```

```bash
export OPENAI_API_KEY=...
uv run tauon run examples/weather.py --message "What's the weather in Paris?"
```
