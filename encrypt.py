import base64,json,os,re
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
load_dotenv()
TOKEN=os.environ["DISCORD_TOKEN"]
PASSWORD=os.environ["ENCRYPTION_PASSWORD"]
JS_FILE="emberbot137.js"
ITERATIONS=600_000
def encrypt(text,password):
    salt=os.urandom(16)
    iv=os.urandom(12)
    kdf=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=ITERATIONS)
    key=kdf.derive(password.encode())
    ciphertext=AESGCM(key).encrypt(iv,text.encode(),None)
    return json.dumps({"salt":base64.b64encode(salt).decode(),"iv":base64.b64encode(iv).decode(),"ciphertext":base64.b64encode(ciphertext).decode()})
with open(JS_FILE,"r",encoding="utf-8") as file:
    javascript=file.read()
encrypted_token=encrypt(TOKEN,PASSWORD)
javascript=re.sub(r'const ENCRYPTED_BOT_TOKEN=`.*?`;',f'const ENCRYPTED_BOT_TOKEN=`{encrypted_token}`;',javascript,count=1)
with open(JS_FILE,"w",encoding="utf-8") as file:
    file.write(javascript)
print("Encrypted bot token written to ",JS_FILE)