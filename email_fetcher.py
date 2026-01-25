import imaplib # Connects to email inbox using IMAP
import email # Helps read and parse email messages
from email.header import decode_header # Decodes subjects
from email.utils import parsedate_to_datetime # Converts email date string to Python datetime
import mysql.connector
from config import DB_CONFIG
import os
from dotenv import load_dotenv


load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_HOST = "imap.gmail.com" # Gmail’s IMAP server

# This function receives one email message and extracts
def extract_email_details(msg):
    raw_subject, enc = decode_header(msg["Subject"])[0] # handles encoded subject

    """
    If subject is bytes → decode it
    If it’s already a string → use it directly
    """
    subject = raw_subject.decode(enc or "utf-8") if isinstance(raw_subject, bytes) else raw_subject

    # From field
    raw_from, enc_from = decode_header(msg["From"])[0]
    if isinstance(raw_from, bytes):
        from_field = raw_from.decode(enc or "utf-8")
    else:
        from_field = raw_from

    # Organization
    if "<" in from_field:
        org = from_field.split("<")[0].strip()
    else:
        org = from_field

    # Date
    date_header = msg.get("Date")
    applied_date = parsedate_to_datetime(date_header).date() if date_header else None

    # Message-ID (unique identifier)
    message_id = msg.get("Message-ID")

    # Job title (try to extract from body)
    job_title = None
    keywords = ["applied for", "application for", "position", "role"]

    if msg.is_multipart(): # can be HTML + text + attachments
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                # naive extraction example
                for key in keywords:
                    if key in body.lower():
                        text = body.lower().split(key)[1].strip()
                        # stop at punctuation
                        for stop in [".", ",", "!", "?"]:
                            if stop in text:
                                text = text.split(stop)[0]
                                break

                        # limit to first few words
                        words = text.split()
                        job_title = " ".join(words[:5]).strip()
                        break
                        #job_title = body.lower().split(key)[1].split("\n")[0].strip()

    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
        for key in keywords:
            if key in body.lower():
                text = body.lower().split(key)[1].strip()
                # stop at punctuation
                for stop in [".", ",", "!", "?"]:
                    if stop in text:
                        text = text.split(stop)[0]
                        break

                # limit to first few words
                words = text.split()
                job_title = " ".join(words[:4]).strip()
                break

    return {
        "organization": org,
        "job_title": job_title,
        "applied_date": applied_date,
        "subject": subject,
        "message_id": message_id
    }

def save_to_db(data_list):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    query = """
        INSERT IGNORE INTO applications (organization, job_title, applied_date, city, message_id)
    VALUES (%s, %s, %s, %s, %s)
    """

    for item in data_list:
        cursor.execute(query, (
            item["organization"],
            item["job_title"],
            item["applied_date"],
            item["city"],
            item["message_id"]
        ))

    conn.commit()
    cursor.close()
    conn.close()

def fetch_applied_jobs():
    # Connects to Gmail securely
    # Logs in using app password
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(EMAIL_USER, EMAIL_PASS)

    status, labels = mail.list()
    job_labels = []

    for label in labels:
        print(label.decode())

    for label in labels:
        decoded = label.decode()
        if "Applied Job - " in decoded:
            # Extract the IMAP folder name inside quotes
            folder = decoded.split(' "/" ')[1].strip('"')
            job_labels.append(folder)

    results = []

    for folder in job_labels:
        status, _ = mail.select(f'"{folder}"')
        # Extract city name
        city = folder.split("-")[1].strip()
        status, data = mail.search(None, "All")

        for num in data[0].split():
            # Fetches full email
            # Converts bytes → email object
            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            details = extract_email_details(msg)
            details["city"] = city  # add city to the dictionary
            results.append(details)

    mail.logout()
    return results







