# Zorven Community Release Notes

## Included

- Discord-style web community client
- Windows desktop community client
- Account registration and login
- Staff role tags for `admin`, `staff`, `moderator`, and `zorven`
- Text channels and persistent messages
- Local matchmaking queue endpoint
- Test-only checkout endpoint
- Downloadable client placeholder
- PBKDF2 password hashing for new accounts
- Basic security headers and escaped chat content

## Start

Run `start_zorven.bat` for the web client or `start_zorven_chat.bat` for the desktop client. Both require Python 3.10+.

## Before public release

Replace the local JSON store with a hosted database, add HTTPS, use a real session store, configure backups, integrate a payment provider, replace the client placeholder, and deploy behind a production web server.
