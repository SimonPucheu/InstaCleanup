# Instagram message cleanup

A small Python script that unsends only messages sent by the logged-in account
in one Instagram group. It skips system messages and saves progress locally so
the run can be resumed.

## Run on Linux

Install Python 3 and virtual-environment support first. On Debian or Ubuntu:

```sh
sudo apt update
sudo apt install python3 python3-venv
```

Then, from the project directory:

```sh
cp config.example.json config.json
# Edit config.json with the Instagram group ID and exact group title
chmod +x ./run-linux.sh
./run-linux.sh
```

The launcher creates a project-local `.venv` and installs the pinned
dependencies from `requirements.txt`. On first run, the script asks for the
Instagram username and password in the terminal. It asks for a two-factor
authentication code if needed.

You can also set up and run it manually:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python nettoyage.py
```

## Local files and privacy

The Instagram session (`session.json`) and resume state (`etat.json`) are stored
beside the script and are ignored by Git. The local group configuration
(`config.json`) is ignored too. Do not share `session.json`; it can provide
access to your account. Do not commit it or paste its contents into an issue or
chat.

If you stop the script with Ctrl+C, run it again to resume from its saved
progress. The script also stops when Instagram requires a check or asks you to
slow down.

If login returns HTTP 429, Instagram is rate-limiting the account or request.
Do not keep retrying or try to bypass the limit. Check the account in the
official Instagram app and wait before attempting another login.

## Important

This project uses an unofficial Instagram client. Instagram may change its
interfaces, require verification, rate-limit requests, or restrict an account.
Use it at your own risk and review the code before running it.

Set `group_id` and `group_name` in your local `config.json`; the example file
contains placeholders and is safe to commit.
