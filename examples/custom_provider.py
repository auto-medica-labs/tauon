"""Use any OpenAI-compatible provider with Tauon via api_key/base_url.

Pass api_key= and base_url= to run_agent().  When either is set, Tauon
skips its model catalog and creates a plain OpenAI-compatible provider
pointed at your endpoint.

    uv run python examples/custom_provider.py
"""

import os

import anyio

from tauon import define_agent, run_agent, use_model


@define_agent
def SimpleAgent() -> str:
    # Note: this use_model() is overridden by model= in run_agent() below.
    # The model= kwarg wins over use_model() when both are set.
    use_model("gpt-5.6-luna")
    return "Reply concisely."


# ---------------------------------------------------------------------------
# Example: Any OpenAI-compatible endpoint (vLLM, Together, etc.)
# ---------------------------------------------------------------------------
async def generic_endpoint() -> None:
    """Point at any OpenAI-compatible chat completions endpoint."""
    reply = await run_agent(
        SimpleAgent,
        "Say hello in French.",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="qwen/qwen3.5-9b",
    )
    print(f"Agent: {reply}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
async def main() -> None:
    print("--- OpenAI-compatible provider examples ---\n")
    await generic_endpoint()


if __name__ == "__main__":
    anyio.run(main)
