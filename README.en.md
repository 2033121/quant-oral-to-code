[中文](README.md) | English

# quant-oral-to-code

`quant-oral-to-code` is an open-source skill for quant beginners and general-purpose
agents. It turns a natural-language strategy idea into a **checkable, re-runnable,
explainable strategy workspace skeleton** — it deliberately does *not* promise
research-grade return figures. A condensed English guide is kept here; the
[Chinese README](README.md) is the authoritative full reference.

## What it does

A fixed pipeline turns what you say into what can be audited:

1. **intake** — collect the spoken strategy, data conditions, expected outputs
2. **dsl** — compress the narration into a structured strategy spec
3. **guardrails** — review look-ahead bias, overfitting, missing out-of-sample and optimistic fill assumptions
4. **codegen** — generate a strategy code skeleton + backtest entrypoint
5. **report** — delivery notes, limitations, next steps

## Non-negotiable rules

- **DuckDB is the only standard persistence format** (`generated_strategies/<slug>/data/normalized/market.duckdb`, table `bars`, PK `[symbol, trade_date]`). CSV/Parquet/JSON/SQLite/API inputs must normalize into DuckDB before entering the unified pipeline.
- **`data_required_cutoff` is mandatory**, not optional: when real data, field mappings, key columns or the minimal data contract are missing, the pipeline stops at artifacts-only mode. It must not be dressed up as a "completed backtest".
- **Claim levels**: `demo_only` / `portable_backtest` / `research_grade_local`. Default summaries report claim level, decision, guardrail hints, action counts and sample size — never realized returns, max drawdown or Sharpe until a real PnL/equity-curve evidence chain is wired in.

## Install (agents)

Drop `skills/quant-oral-to-code/` into any SKILL.md-compatible agent directory
(Claude Code `~/.claude/skills/`, Codex CLI `~/.codex/skills/`, ZCode
`~/.zcode/skills/`, DSH `~/.dsh/skills/`), or use the repo installer:

```bash
bash adapters/install.sh --all        # symlink install + frontmatter validation
python3 adapters/build_prompt_pack.py # single-file prompt pack for chat agents
```

For chat-only agents (no filesystem, e.g. WorkBuddy): paste
`adapters/prompt-pack/quant-oral-to-code-pack.md` to translate strategy ideas into
a structured spec + guardrail review. Script execution and real backtests require
a filesystem agent; chat agents cap at `demo_only` ("spec transcription only").

## Repo-name release bundles

Release bundles ship in four layouts (claude / mimo / codex / legacy skill-pack).
If an agent "cannot find the skill", check that you did not add one extra wrapper
dir — correct results are `.../skills/quant-oral-to-code/SKILL.md` (or with an
outer `skills/` container: `.../skills/skills/quant-oral-to-code/SKILL.md`).

Rebuild all release artifacts:

```bash
python3 skills/quant-oral-to-code/scripts/build_release_bundle.py --output-dir ../packages --layout all --zip
```

## Validation

```bash
# structure-only, no side effects
python3 skills/quant-oral-to-code/scripts/validate_quant_oral_to_code.py
# full chain (has workspace side effects within the fixed demo slugs)
python3 skills/quant-oral-to-code/scripts/run_full_validation.py
```

Dependencies: `pip install -r requirements.txt` (duckdb, jsonschema; pandas is
optional, only needed by some data tools). CI runs both levels on every push/PR.

## Docs

- [Scope & boundaries of the open-source edition](docs/2026-06-22-quant-oral-to-code.md)
- [A-share data sources](docs/2026-06-22-a-share-data-sources.md)

## License

MIT
