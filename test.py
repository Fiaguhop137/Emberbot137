import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
SCOPES=["https://www.googleapis.com/auth/documents"]
DOCUMENT_ID="1WHjzHm3_poLQ51OLn5nvGkzArWMzogc2tEgYgcXRc_g"
if os.path.exists("token.json"):
    creds=Credentials.from_authorized_user_file("token.json",SCOPES)
else:
    creds=None
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow=InstalledAppFlow.from_client_secrets_file("credentials.json",SCOPES)
        creds=flow.run_local_server(port=0)
    with open("token.json","w") as token:
        token.write(creds.to_json())
docs=build("docs", "v1", credentials=creds)
def get_document():
    return docs.documents().get(documentId=DOCUMENT_ID).execute()
def trim(maxlines):
    document=get_document()
    paragraphs=[]
    for element in document["body"]["content"]:
        if "paragraph" in element:
            paragraphs.append(element)
    extra=len(paragraphs)-maxlines
    if extra>0:
        docs.documents().batchUpdate(documentId=DOCUMENT_ID,body={"requests":[{"deleteContentRange":{"range":{"startIndex":paragraphs[0]["startIndex"],"endIndex":paragraphs[extra-1]["endIndex"]}}}]}).execute()
def append_text(text):
    document=get_document()
    end_index=document["body"]["content"][-1]["endIndex"]
    docs.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={"requests":[{"insertText":{"location":{"index":end_index-1},"text":text}}]}).execute()