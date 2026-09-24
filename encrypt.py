import base64,json,os,re
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
load_dotenv()
TOKENS=[os.environ[f"DISCORD_TOKEN_{i}"] for i in range(2)]
PASSWORDS=[os.environ[f"ENCRYPTION_PASSWORD_{i}"] for i in range(2)]
USERNAMES=[os.environ[f"USERNAME_{i}"] for i in range(2)]
JS_FILE="discord.js"
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
encrypted_tokens=[]
for i,(TOKEN,PASSWORD) in enumerate(zip(TOKENS,PASSWORDS)):
    encrypted_token=encrypt(TOKEN,PASSWORD)
    encrypted_tokens.append(encrypted_token)
compiled_tokens="const ENCRYPTED_BOT_TOKENS={"
for i,encrypted_token in enumerate(encrypted_tokens):
    compiled_tokens=compiled_tokens+f"{i}:`{encrypted_token}`,"
compiled_tokens=compiled_tokens[:-1]+"};"
javascript=re.sub(r'const ENCRYPTED_BOT_TOKENS={.*?};',compiled_tokens,javascript,count=1,flags=re.DOTALL)
compiled_usernames="const USERNAMES=["
for i in range(len(USERNAMES)):
    compiled_usernames=compiled_usernames+f'"{USERNAMES[i]}",'
compiled_usernames=compiled_usernames[:-1]+"];"
javascript=re.sub(r'const USERNAMES=\[.*?\];',compiled_usernames,javascript,count=1,flags=re.DOTALL)
with open(JS_FILE,"w",encoding="utf-8") as file:
    file.write(javascript)
print("Encrypted bot token written to ",JS_FILE)