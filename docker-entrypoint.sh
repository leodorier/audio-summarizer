#!/bin/sh
# Entrypoint for the audio-summarizer container.
#
# The app writes its SQLite database and media files into /app/storage, which
# is a bind mount shared with the host and may still contain files owned by
# root from earlier (root-ful) runs. Drop privileges to the unprivileged
# `appuser` for the application process, but first normalise ownership of the
# storage tree so SQLite can create/update the DB and its -wal/-shm siblings.
#
# This block only runs when the container starts as root; if the image is
# already configured to run unprivileged it is skipped and the app runs
# as-is. The app source is provided via the ./app bind mount and is read-only
# from the app's perspective.
set -eu

APP_UID="${APP_UID:-1000}"
APP_GID="${APP_GID:-1000}"

if [ "$(id -u)" = "0" ]; then
    if [ -d /app/storage ]; then
        chown -R "${APP_UID}:${APP_GID}" /app/storage 2>/dev/null || true
    fi
    exec setpriv --reuid="${APP_UID}" --regid="${APP_GID}" --init-groups "$@"
fi

exec "$@"
