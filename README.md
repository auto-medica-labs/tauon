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
    use_model("gpt-4.1-mini")
    use_tool(get_weather)
    return "You are a weather assistant."
```

```bash
export OPENAI_API_KEY=...
uv run tauon run examples/weather.py --message "What's the weather in Paris?"
```

## Models and environment variables

Tauon resolves models from Tau's built-in provider catalog. API keys are read
from environment variables only; Tauon does **not** load saved credentials from
`~/.tau/credentials.json` or provider preferences from `~/.tau/providers.json`.

### `use_model()` patterns

```python
# Bare model name: resolved against the default provider (openai).
use_model("gpt-4.1-mini")  # needs OPENAI_API_KEY

# provider/model syntax: required when the model ID contains "/" or when you
# want to force a specific provider.
use_model("openai-codex/gpt-5.6-luna")  # needs OPENAI_CODEX_ACCESS_TOKEN
use_model("openrouter/qwen/qwen3-14b")  # needs OPENROUTER_API_KEY
use_model("anthropic/claude-sonnet-4-6")  # needs ANTHROPIC_API_KEY
```

### Provider environment variables

| Provider                | Env var                         | Example `use_model()`                                           |
| ----------------------- | ------------------------------- | --------------------------------------------------------------- |
| `openai`                | `OPENAI_API_KEY`                | `use_model("gpt-4.1-mini")`                                     |
| `openai-codex`          | `OPENAI_CODEX_ACCESS_TOKEN`     | `use_model("openai-codex/gpt-5.6-luna")`                        |
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

Bare model names (e.g. `use_model("gpt-4.1-mini")`) resolve against the
default provider, which is `openai`. Use the `provider/model` syntax for every
other provider. For OpenRouter the prefix is required because model IDs contain
`/`, e.g. `use_model("openrouter/qwen/qwen3-14b")`.

Model names not yet in Tau's built-in catalog fall back to a plain
OpenAI-compatible provider using `OPENAI_API_KEY` (a warning is logged). This
keeps newly-released models usable immediately, but it also means a typo'd
model name is sent to OpenAI rather than failing at startup — use the
`provider/model` syntax to force a specific provider.

For a provider not in the catalog, or to override the endpoint explicitly, pass
`api_key` and `base_url` directly to `run_agent()` as shown in
[`examples/custom_provider.py`](examples/custom_provider.py).

## Changelog

### 0.1.0

Breaking changes from 0.0.1:

- `run_agent()` now returns only the text of the **final** assistant message.
  Multi-turn tool use no longer concatenates intermediate reasoning prose; if
  the provider ends with no text, the result is an empty string.
- Provider transport errors are wrapped in a `RuntimeError` with a
  `Provider error:` message prefix (the original exception is preserved as
  `__cause__` and logged). 0.0.1 propagated the raw provider exception
  (e.g. `ConnectionError`).

Also fixed:

- `tauon run <script>` keeps the script's directory importable for the whole
  run, so sibling imports inside agent/tool bodies work lazily at run time,
  matching `python script.py` semantics.
