# Zorven Community

A self-contained Discord-style community application with account registration,
login, channel chat, staff identities, and server creation.

## Run locally

Requires Python 3.10 or newer. From the repository root:

```bash
python3 zorven/server.py
```

Open `http://127.0.0.1:8765/login` in a browser. The custom maintenance page is
available at `http://127.0.0.1:8765/maintenance`. On Windows, run
`zorven/start_zorven.bat` instead.

## Desktop and mobile app notes

The desktop launcher in `zorven/desktop_app.py` connects to the same backend, but
it can also point at a custom host instead of hard-coded localhost.

Examples:

```bash
ZORVEN_API_URL="https://api.example.com" python3 zorven/desktop_app.py
python3 zorven/desktop_app.py --host https://api.example.com
```

On Windows, you can also launch the desktop client with a custom API host:

```bat
zorven\start_zorven_chat.bat https://api.example.com
```

The browser app is fully mobile-friendly and uses the same API host your server
is serving on. A hosted custom domain can be used for both the web app and the
PC desktop client by setting the same API URL.

## Verify before release

```bash
python3 -m py_compile zorven/server.py zorven/desktop_app.py
```

Then verify registration, login, sending a message in each channel, mobile
navigation, and the staff moderation flow with stagicd /workspaces/zorven
export SETUP_KEY='Zorven-Setup-2026-Alpha-7f9d2c1e-Q7R9xM2k'
python3 zorven/server.pyg accounts. See
`zorven/RELEASE_NOTES.md` for the infrastructure required before a public
internet deployment.

## Deploy to Render

The repository includes `render.yaml`. In the Render dashboard, select **New +**
then **Blueprint**, connect this repository, and apply the detected Blueprint.
It starts the service with `python zorven/server.py`, uses `/api/health` for
health checks, and serves the app on the `PORT` supplied by Render.

The Blueprint provisions a 1 GB persistent disk at `/var/data` and sets
`DATA_FILE` to `/var/data/zorven_data.json`; this preserves accounts and chat
messages across deploys and restarts. Persistent disks require a paid Render web
service, so select the configured Starter plan or a larger paid plan.

Before connecting a custom domain, create a staging account, test registration,
login, messaging, and a restart from the Render dashboard. Render terminates
HTTPS for its supplied URL and custom domains.
