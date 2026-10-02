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

## Prompts

Long system prompts are better kept in a markdown/text file than returned
from the agent body. Load one with `use_prompt()`:

```python
from tauon import define_agent, use_model, use_prompt


@define_agent
def WeatherAgent() -> None:
    use_model("openai/gpt-4.1-mini")
    use_prompt("prompt.md")
```

Relative paths resolve against the directory of the module that defines the
agent, so `tauon run` works from any launch directory. Agents defined without
a module file (REPL, `-c`) fall back to the current working directory.
`use_prompt()` and returning a prompt string from the agent are mutually
exclusive — using both raises a `RuntimeError`. See
[`examples/markdown_prompt.py`](examples/markdown_prompt.py).

## Models and environment variables

Tauon resolves models from Tau's built-in provider catalog. API keys are read
from environment variables only. Tauon never reads or writes `$TAU_HOME`
(`~/.tau`): it does not load saved credentials (`credentials.json`),
preferences (`providers.json`), catalog overlays (`catalog.toml`), or the
refreshed `models-store.json`. Codex subscription auth (`openai-codex/*`) is
not supported — use an API-key provider.

### `use_model()` patterns

```python
# provider/model syntax is required.
use_model("openai/gpt-4.1-mini")  # needs OPENAI_API_KEY
use_model("openrouter/qwen/qwen3-14b")  # needs OPENROUTER_API_KEY
use_model("anthropic/claude-sonnet-4-6")  # needs ANTHROPIC_API_KEY
```

### Provider environment variables

| Provider                | Env var                         | Example `use_model()`                                           |
| ----------------------- | ------------------------------- | --------------------------------------------------------------- |
| `openai`                | `OPENAI_API_KEY`                | `use_model("openai/gpt-4.1-mini")`                             |
| `anthropic`             | `ANTHROPIC_API_KEY`             | `use_model("anthropic/claude-sonnet-4-6")`                      |
| `google`                | `GEMINI_API_KEY`                | `use_model("google/gemini-2.5-pro")`                            |
| `deepseek`              | `DEEPSEEK_API_KEY`              | `use_model("deepseek/deepseek-v4-pro")`                         |
| `xai`                   | `XAI_API_KEY`                   | `use_model("xai/grok-3")`                                       |
| `groq`                  | `GROQ_API_KEY`                  | `use_model("groq/llama-3.1-8b-instant")`                        |
| `cerebras`              | `CEREBRAS_API_KEY`              | `use_model("cerebras/gpt-oss-120b")`                            |
| `nvidia`                | `NVIDIA_API_KEY`                | `use_model("nvidia/llama-3.3-nemotron-super-49b-v1.5")`         |
| `openrouter`            | `OPENROUTER_API_KEY`            | `use_model("openrouter/qwen/qwen3-14b")`                        |
| `huggingface`           | `HF_TOKEN`                      | `use_model("huggingface/Qwen/Qwen3-235B-A22B")`                 |
| `fireworks`             | `FIREWORKS_API_KEY`             | `use_model("fireworks/accounts/fireworks/models/glm-5p1")`      |
| `together`              | `TOGETHER_API_KEY`              | `use_model("together/Qwen/Qwen3-235B-A22B-Instruct-2507-tput")` |
| `mistral`               | `MISTRAL_API_KEY`               | `use_model("mistral/codestral-latest")`                         |
| `minimax`               | `MINIMAX_API_KEY`               | `use_model("minimax/MiniMax-M3")`                               |
| `minimax-cn`            | `MINIMAX_CN_API_KEY`            | `use_model("minimax-cn/MiniMax-M3")`                            |
| `moonshotai`            | `MOONSHOT_API_KEY`              | `use_model("moonshotai/kimi-k2-0711-preview")`                  |
| `moonshotai-cn`         | `MOONSHOT_API_KEY`              | `use_model("moonshotai-cn/kimi-k2-0711-preview")`               |
| `kimi-code`             | `KIMI_CODE_API_KEY`             | `use_model("kimi-code/kimi-for-coding")`                        |
| `zai`                   | `ZAI_API_KEY`                   | `use_model("zai/glm-5.1")`                                      |
| `xiaomi`                | `XIAOMI_API_KEY`                | `use_model("xiaomi/mimo-v2-pro")`                               |
| `xiaomi-token-plan-cn`  | `XIAOMI_TOKEN_PLAN_CN_API_KEY`  | `use_model("xiaomi-token-plan-cn/mimo-v2-pro")`                 |
| `xiaomi-token-plan-ams` | `XIAOMI_TOKEN_PLAN_AMS_API_KEY` | `use_model("xiaomi-token-plan-ams/mimo-v2-pro")`                |
| `xiaomi-token-plan-sgp` | `XIAOMI_TOKEN_PLAN_SGP_API_KEY` | `use_model("xiaomi-token-plan-sgp/mimo-v2-pro")`                |
| `vercel-ai-gateway`     | `AI_GATEWAY_API_KEY`            | `use_model("vercel-ai-gateway/alibaba/qwen-3-235b")`            |
| `opencode`              | `OPENCODE_API_KEY`              | `use_model("opencode/deepseek-v4-pro")`                         |
| `opencode-go`           | `OPENCODE_API_KEY`              | `use_model("opencode-go/kimi-k2.7-code")`                       |
| `github-copilot`        | `COPILOT_GITHUB_TOKEN`          | `use_model("github-copilot/claude-opus-4.5")`                   |

Every model must use `provider/model` syntax; a bare model name raises a
`RuntimeError`. For OpenRouter the model ID itself contains `/`, e.g.
`use_model("openrouter/qwen/qwen3-14b")`.

A model that is not in Tau's built-in catalog for the named provider raises a
`RuntimeError` rather than silently falling back. To point at a provider or
endpoint not in the catalog, pass `api_key` and `base_url` directly to
`run_agent()` as shown in
[`examples/custom_provider.py`](examples/custom_provider.py).
