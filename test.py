import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate(
    "/home/firebot/git/Emberbot137/firebase-service-account.json"
)

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://discord-fia-default-rtdb.firebaseio.com"
})

messages = db.reference("messages")

def on_message(event):
    print("Firebase:", event.data)

messages.listen(on_message)