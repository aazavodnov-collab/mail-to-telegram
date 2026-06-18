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

LAST_UID_FILE = "last_uid.txt"

# ----------------------------
# helpers
# ----------------------------

def decode_mime_words(s):
    if not s:
        return ""
    decoded = decode_header(s)
    return "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in decoded
    )

def get_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))

                if ctype == "text/plain" and "attachment" not in disp:
                    return part.get_payload(decode=True).decode(errors="ignore")

            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True).decode(errors="ignore")
                    return BeautifulSoup(html, "html.parser").get_text()

        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(errors="ignore")

    except:
        return ""

    return ""

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text
        }, timeout=10)
    except Exception as e:
        print("TG ERROR:", e)

# ----------------------------
# read last UID
# ----------------------------

try:
    with open(LAST_UID_FILE, "r") as f:
        last_uid = int(f.read().strip() or "0")
except:
    last_uid = 0

print("LAST UID:", last_uid)

# ----------------------------
# connect IMAP
# ----------------------------

mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(IMAP_USER, IMAP_PASS)
mail.select("INBOX")

status, data = mail.uid("search", None, "ALL")
uids = data[0].split()

new_last_uid = last_uid

print("FOUND UIDS:", len(uids))

# ----------------------------
# process only NEW emails
# ----------------------------

for uid in uids:
    uid_int = int(uid)

    if uid_int <= last_uid:
        continue

    try:
        status, msg_data = mail.uid("fetch", uid, "(RFC822)")

        if not msg_data or not msg_data[0]:
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = decode_mime_words(msg.get("subject"))
        from_ = decode_mime_words(msg.get("from"))
        body = get_body(msg).strip()

        if not body:
            body = "(нет текста)"

        if len(body) > 3000:
            body = body[:3000] + "\n...(обрезано)"

        text = f"""📩 Новое письмо

👤 От: {from_}
📌 Тема: {subject}

📝 {body}
"""

        send_telegram(text)

        new_last_uid = max(new_last_uid, uid_int)

    except Exception as e:
        print("ERROR UID:", uid, e)
        continue

# ----------------------------
# save last UID
# ----------------------------

with open(LAST_UID_FILE, "w") as f:
    f.write(str(new_last_uid))

print("UPDATED LAST UID:", new_last_uid)

mail.logout()
