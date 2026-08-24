# Zorven Community

A self-contained Discord-style community application with account registration,
login, channel chat, staff identities, and server creation.

## Run locally

Requires Python 3.10 or newer. From the repository root:

```bash
python3 zorven/server.py
```

Open `http://127.0.0.1:8765/login` in a browser. On Windows, run
`zorven/start_zorven.bat` instead.

## Verify before release

```bash
python3 -m py_compile zorven/server.py zorven/desktop_app.py
```

Then verify registration, login, sending a message in each channel, mobile
navigation, and the staff moderation flow with staging accounts. See
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