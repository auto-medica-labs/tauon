# Tauon

A minimal Python agent framework built on [`tau`](https://github.com/huggingface/tau).
Think of it like [`flue`](https://github.com/withastro/flue) of `tau` instead of [`pi`](https://github.com/earendil-works/pi).

> **Beta software.** Tauon is a thin layer over tau-ai, which has not yet
> published a stable public SDK. Until that SDK is released, internal APIs may
> change without notice. Not recommended for production use.

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
