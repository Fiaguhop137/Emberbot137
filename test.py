import json
import os
import urllib.request
import urllib.error

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


FIREBASE_CREDENTIALS = "/home/firebot/git/Emberbot137/firebase-service-account.json"
DATABASE_URL = "https://discord-fia-default-rtdb.firebaseio.com"
ENV_FILE = "/home/firebot/git/Emberbot137/.env"


def load_env(path):
    with open(path, "r") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ('"', "'")
            ):
                value = value[1:-1]

            os.environ.setdefault(key, value)


load_env(ENV_FILE)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL is missing from .env")


cred = credentials.Certificate(FIREBASE_CREDENTIALS)

firebase_admin.initialize_app(cred, {
    "databaseURL": DATABASE_URL
})

messages = db.reference("messages")


def send_to_discord(text):
    payload = json.dumps({
        "content": text
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Emberbot137"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            print("Discord webhook:", response.status)
            return True

    except urllib.error.HTTPError as error:
        print("Discord webhook HTTP error:", error.code)
        print(error.read().decode(errors="replace"))
        return False

    except urllib.error.URLError as error:
        print("Discord webhook connection error:", error)
        return False


def on_message(event):
    if event.event_type != "put":
        return

    if event.path == "/":
        return

    data = event.data

    if not isinstance(data, dict):
        return

    text = data.get("data")

    if not text:
        return

    print("NEW MESSAGE:", data)

    if send_to_discord(text):
        key = event.path.strip("/")

        messages.child(key).delete()

        print("Deleted Firebase message:", key)
    else:
        print("Message left in Firebase for retry.")


print("Listening for Firebase messages...")

messages.listen(on_message)