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

### First staff account

Before creating the first staff account, add a `SETUP_KEY` environment variable
in the Render service's **Environment** settings. Use a long, unique value and
keep it private. On the Zorven login screen, select **Set up the first staff
account**, enter that key, and create the account. The first account receives all
staff permissions. This setup path automatically locks after a staff account has
been created; later full-access staff can create additional staff accounts from
the staff panel.

### Zorven Team account

The staff setup dialog also has **Claim the Zorven Team account with this
password**, available while `SETUP_KEY` is set. Enter the setup key and a
password, then use it to sign in as `zorven-team`, a real account with every
staff permission. Re-running this action resets that account's password.

### Admin console

Staff with member management permission see an admin console icon in the chat
sidebar, which opens `/admin` in a new tab. That page is a separate,
authenticated console for viewing service stats, searching accounts, granting or
removing staff status, and banning or unbanning members. It uses the same
sign-in session as the chat client.