# Setup

Setup and run instructions now live in the **[README](README.md)** — see **Quick start**.

TL;DR:
1. `cp env.example .env` and set `ANTHROPIC_API_KEY`.
2. Backend: `pip install -r requirements.txt` then `python -m uvicorn main:app --app-dir backend --port 8000`.
3. Front-end: `npm install` then `npm run dev`.
4. Open **http://localhost:8080**.

Prerequisites: Python 3.11+, Node 18+, [Tectonic](https://tectonic-typesetting.github.io) on `PATH`, and an [Anthropic API key](https://console.anthropic.com).
