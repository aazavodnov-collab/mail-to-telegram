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

    status, msg_data = mail.uid("fetch", uid, "(RFC822)")

    # 🔴 защита от странного ответа IMAP
    if not msg_data or not msg_data[0]:
        print("EMPTY FETCH for UID:", uid)
        continue

    raw = msg_data[0][1]

    # 🔴 защита если вдруг формат другой
    if not raw:
        print("NO RAW DATA for UID:", uid)
        continue

    msg = email.message_from_bytes(raw)

    subject = decode_mime_words(msg["subject"])
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

    print("SENDING TELEGRAM...")
    send_telegram(text)

    print("SENT OK")
    break

    send_telegram(text)

    break


mail.logout()
