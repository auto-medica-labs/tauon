## Changelog

### 0.4.1

- No runtime changes; verifies the tag-triggered PyPI publishing workflow.

### 0.4.0

Breaking changes:

- `use_model()` now requires `provider/model` syntax. Bare model names no
  longer resolve against a default provider; `use_model("gpt-4.1-mini")` now
  raises a `RuntimeError`. Use `use_model("openai/gpt-4.1-mini")`, or pass an
  explicit `provider_name=` (or `api_key=` + `base_url=`) to `run_agent()`.
- The plain OpenAI-compatible fallback for unknown bare model names is removed.
  A model missing from its named provider's catalog raises instead of being
  silently routed to OpenAI.

Also fixed:

- Custom endpoints (`api_key=` / `base_url=`) and injected providers now pass
  the model id through verbatim. Slash-containing ids such as OpenRouter's
  `qwen/qwen3.5-9b` are no longer mistaken for `provider/model` syntax and
  truncated to `qwen3.5-9b`.

### 0.1.5

- Upgrade `tau-ai` from `>=0.3.13` to `>=0.4.7` (no Tauon API changes).
  Notable upstream changes: provider catalog generated from models.dev, Z.AI
  thinking serialization and Anthropic usage-accounting fixes, response-timing
  metadata, and dynamic/extension provider runtimes. Tauon's public API and
  behavior are unchanged.

### 0.1.4

- Upgrade `tau-ai` to `>=0.3.13` (provider protocol now passes `session_id`).
- New `use_prompt()` hook loads the system prompt from a markdown/text file.
  Relative paths resolve against the directory of the module that defines the
  agent, so `tauon run` works from any launch directory; agents defined
  without a module file (REPL, `-c`) fall back to the current working
  directory. `use_prompt()` and returning a prompt string from the agent are
  mutually exclusive — using both raises a `RuntimeError`.

### 0.1.3

- Upgrade `tau-ai` to `>=0.3.5` (prompt-cache retention settings, Codex
  token-refresh locking; no API changes).

### 0.1.0

Breaking changes from 0.0.1:

- `run_agent()` now returns only the text of the **final** assistant message.
  Multi-turn tool use no longer concatenates intermediate reasoning prose; if
  the provider ends with no text, the result is an empty string.
- Provider transport errors are wrapped in a `RuntimeError` with a
  `Provider error:` message prefix (the original exception is preserved as
  `__cause__` and logged). 0.0.1 propagated the raw provider exception
  (e.g. `ConnectionError`).
- `tauon run` now rejects modules that define more than one agent — 0.0.1
  silently ran the first one found. Keep exactly one `@define_agent` function
  per module.
- The `ToolLike` type alias is removed (`tauon.tool` / `tauon._types`); use
  `AgentTool` instead.
- `@define_agent` rejects async functions with a `TypeError` (they were never
  supported and failed confusingly before).

Also fixed:

- `tauon run <script>` keeps the script's directory importable for the whole
  run, so sibling imports inside agent/tool bodies work lazily at run time,
  matching `python script.py` semantics.
