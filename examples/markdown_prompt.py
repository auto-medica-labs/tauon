"""System prompt loaded from a markdown file via the ``use_prompt`` hook.

``use_prompt(\"prompt.md\")`` takes a bare relative path — it resolves
against this script's directory, so it works no matter where you launch
``tauon run`` from.
"""

from tauon import define_agent, define_tool, use_model, use_prompt, use_tool


@define_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny and 22°C in {city}."


@define_agent
def WeatherAgent() -> None:
    use_model("gpt-5.6-luna")
    use_tool(get_weather)
    use_prompt("prompt.md")
