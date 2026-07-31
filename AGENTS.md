# AGENTS.md

## Project overview
- This repository contains a Python Discord moderation and utility bot.
- Keep prefix commands (`?command`) and slash commands (`/command`) in sync: every user-facing bot command should have both forms unless a command is inherently prefix-only.

## Development guidelines
- Prefer small, dependency-light Python modules.
- Run `python -m py_compile bot.py` after changing Python code.
- Do not commit secrets. Use `.env` locally and document required variables in `.env.sample`.
