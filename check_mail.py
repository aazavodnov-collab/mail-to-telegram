import imaplib
import email
import os
import requests
from email.header import decode_header
from bs4 import BeautifulSoup

IMAP_SERVER = "mail.hosting.reg.ru"
IMAP_USER = os.environ["IMAP_USER"]
IMAP_PASS = os.environ["IMAP_PASS"]

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def decode_mime_words(s):
    if not s:
        return ""
    decoded = decode_header(s)
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in decoded
    )

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")

        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                return BeautifulSoup(html, "html.parser").get_text()

    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="ignore")

    return ""

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })

# -----------------------------
# IMAP CONNECT
# -----------------------------
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(IMAP_USER, IMAP_PASS)
mail.select("INBOX")

# -----------------------------
# UID SEARCH (ВАЖНО)
# -----------------------------
status, data = mail.uid("search", None, "ALL")
uids = data[0].split()

print("FOUND UIDS:", len(uids))

# -----------------------------
# PROCESS EMAILS
# -----------------------------
for uid in uids:
    print("UID:", uid)
    send_telegram("DEBUG: loop works, UID received")
    break


mail.logout()
