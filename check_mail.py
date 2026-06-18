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
    # если письмо multipart
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # берём текстовую часть
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")

        # если text/plain нет — пробуем HTML
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

mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(IMAP_USER, IMAP_PASS)
mail.select("inbox")

status, messages = mail.search(None, "UNSEEN")

print("STATUS:", status)
print("MESSAGES:", messages)
print("FOUND COUNT:", len(messages[0].split()) if messages[0] else 0)

for num in messages[0].split():
    send_telegram("TEST: Telegram работает")
    status, msg_data = mail.fetch(num, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    subject = decode_mime_words(msg["subject"])
    from_ = decode_mime_words(msg.get("from"))
    body = get_body(msg).strip()

    # обрезаем, чтобы Telegram не ругался на лимит
    if len(body) > 3500:
        body = body[:3500] + "\n\n…(обрезано)"

    text = f"""📩 <b>Новое письмо</b>

👤 <b>От:</b> {from_}
📌 <b>Тема:</b> {subject}

📝 <b>Текст:</b>
{body}
"""

    send_telegram(text)

mail.logout()
