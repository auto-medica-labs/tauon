## Changelog

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
