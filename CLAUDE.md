# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Discord bot (`talesbot`) for the Shadowrun LARP "Tales from the Sprawl". It runs a Discord bot and a small FastAPI HTTP server in the same process. Python ≥ 3.12, managed with `uv`.

## Commands

```sh
uv sync                 # install dependencies
uv run talesbot         # start bot + API (needs env vars, see below)
uv run ruff check .     # lint (rules: E, F, UP, B, SIM, I — configured in pyproject.toml)
uv run ruff format .    # format
uv run pyright          # type check (standard mode, uses .venv)
docker compose up       # run in a container; mounts ./config and reads .env
```

There is no test suite.

Helper CLI scripts in `src/scripts/` (click-based) work on the config files offline: `uv run import <csv> [out]` (turn a character-sheet CSV into the older `known_handles.conf` format; the bot now reads `config/known_handles.csv` directly) and `uv run unclaimed <known_handles> <handles>` (list handles no player has claimed).

Docker images are published to GHCR by `.github/workflows/docker-publish.yml` when a `v*.*.*` tag is pushed.

## Configuration

`src/talesbot/config.py` loads settings with pydantic-settings from the environment or `.env`. Required: `DISCORD_TOKEN`, `APPLICATION_ID`, `GUILD_NAME`, `GM_ROLE_NAME`, `MAIN_SHOP_NAME`, `FILE_LOGGING`. Optional: `HOST`/`PORT` (API, default `127.0.0.1:5000`), plus these flags:
- `CLEAR_ALL`: wipe players, handles, chats, shops and other game state on startup.
- `DESTROY_ALL`: delete all channels, categories and bot roles in the guild, then exit.
- `SKIP_CHANNELS`: skip channel initialization on startup.

`CLEAR_ALL` and `DESTROY_ALL` are destructive against a live Discord server.

## Architecture

**Entry point** (`src/talesbot/__init__.py`): creates the `config/` subfolders, then runs the Discord bot and the uvicorn/FastAPI server together in an `asyncio.TaskGroup` on uvloop.

**Bot** (`bot.py`): `TalesBot` loads the cogs listed in `__init__.py` (`handles`, `finances`, `chats`, `shops`, and the ones under `ext/`). New cogs must be added to that list. Slash commands are copied to each guild and synced when the guild becomes available. `on_ready` runs the domain modules' `init()` functions in a fixed order (server → handles → actors → players → channels → finances → chats → shops → groups → reactions → gm), then calls `game.start_game()`.

**Message routing** (`bot.py:on_message`): what happens to a message depends on the channel's category or name (checks in `channels.py`). Command-line channels process `.`-prefixed text commands. Chat hubs and landing pages allow a limited set. Anonymous and pseudonymous channels are reposted through `posting.py`, and chat channels go to `chats.py`. Commands typed anywhere else are swallowed (deleted) by `server.swallow`. The `off` category is ignored completely. `game.py` holds the global network state (`NotStarted`/`Ready`/`Down`); while it isn't `Ready`, only chat commands and out-of-game chats get through.

**Commands**: most user-facing commands are `app_commands` (slash commands) in `commands.Cog` classes, either in the domain modules or in `ext/`. Each module has an `async def setup(bot)`. Permissions come from role checks (`common.player_role_name`, the GM role, and so on). Throw `errors.ReportError` to show the user an ephemeral error embed. `TalesCommandTree.on_error` handles it. Persistent Discord UI views live in `ui/`, and `RegisterView` is registered in `setup_hook`.

**Domain model**: A Discord user is a *player*. Players and NPC *actors* (`actors.py`) own one or more *handles* (`handles.py`, the in-game identities, including burners and NPC handles). Money is tracked per handle (`finances.py`). Other domain modules are `chats.py`, `shops.py` (catalogues, storefronts, orders, deliveries), `groups.py`, `scenarios.py` and `artifacts.py`. `channels.py` and `server.py` create and manage Discord categories, channels, roles and permission overwrites. Players get personal roles and channels. `known_handles.py` reads `config/known_handles.csv` (pre-registered handles and what they unlock) when a player runs `/join <handle>`.

**Persistence**: there is no database. All state is stored in `configobj` INI files under `config/` (gitignored, and a volume mount in Docker), one folder per domain, e.g. `config/players/__players.conf`, `config/handles/…`, `config/shops/…`. Modules usually open the `ConfigObj` again on each access and call `.write()` after changing it. Keys beginning with `___`/`__` are internal index sections (e.g. `___user_id_to_player_id`). Handle and player creation runs under `handles.semaphore()` to avoid races.

**HTTP API** (`api.py`): `GET /api/balance/{handle}` and `POST /api/transfer`, used by external in-game devices. Before a transfer, handle IDs pass through `sincard.map_handle`, which applies the optional mapping in `config/sincards.json`.

**Logging** (`logger.py`): when `FILE_LOGGING` is set, log files go to `config/logs/`. The `talesbot.messages` logger records every message the bot sees.
