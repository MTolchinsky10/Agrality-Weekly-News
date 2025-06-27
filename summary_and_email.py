#!/usr/bin/env python3
import glob
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
import requests
import zipfile
import io
import shutil

OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
API_URL = f'https://api.github.com/repos/{OWNER}/{REPO}/actions/artifacts'

# Load token from environment variable
token = os.getenv("GITHUB_TOKEN")
if not token:
    print("❌ Missing GitHub token. Set GITHUB_TOKEN", file=sys.stderr)
    sys.exit(1)

# Common headers
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

artifact_dir = "artifacts_json"  # Default artifact directory

def fetch_and_process_artifacts():
    total_count = 0
    page = 1
    per_page = 1000

    os.makedirs(artifact_dir, exist_ok=True)

    while True:
        params = {'page': page, 'per_page': per_page}
        response = requests.get(API_URL, headers=headers, params=params)

        if response.status_code != 200:
            print(f'❌ Error fetching artifacts: {response.status_code} {response.text}')
            return

        data = response.json()
        artifacts = data.get('artifacts', [])
        total_count += len(artifacts)

        # Process each artifact (download and delete)
        for artifact in artifacts:
            artifact_id = artifact['id']
            artifact_name = artifact['name']
            download_url = artifact['archive_download_url']

            # Download artifact
            print(f"⬇️ Downloading artifact: {artifact_name}")
            download_response = requests.get(download_url, headers=headers)
            if download_response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(download_response.content)) as z:
                    z.extractall(artifact_dir)
                print(f"✅ Extracted to {artifact_dir}")
            else:
                print(f"❌ Failed to download {artifact_name}: {download_response.status_code}")

        if len(artifacts) < per_page:
            break
        page += 1

    print(f"Total artifacts processed: {total_count}")

def load_and_merge(input_dir):
    seen = set()
    merged = {}
    print(f"🔍 Loading and merging files from {input_dir}...")
    for path in glob.glob(f"{input_dir}/RSS_FEEDS_*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load {path}: {e}", file=sys.stderr)
            continue
        for source, articles in data.items():
            merged.setdefault(source, [])
            for art in articles:
                key = art["link"]
                if key not in seen:
                    seen.add(key)
                    merged[source].append(art)
    print(f"🔄 Merged {len(merged)} sources.")
    return merged

def build_email_body(merged, days_desc="último período"):
    from collections import defaultdict

    body = "<h2>📰 Resumen Semanal de Noticias Agro</h2>\n"
    body += f"<p>📅 Noticias del {days_desc} (generado: {datetime.now().strftime('%d/%m/%Y %H:%M')})</p>\n"

    categorized = defaultdict(list)

    for articles in merged.values():
        for article in articles:
            matched_keywords = article.get("matched_keywords", [])
            dt = ""
            if "published" in article:
                try:
                    dt = datetime.fromisoformat(article["published"]).strftime("%d/%m %H:%M")
                except:
                    dt = article["published"]

            for kw in matched_keywords:
                categorized[kw].append((dt, article["title"], article["link"]))

    # Ordenar keywords alfabéticamente para consistencia
    for kw in sorted(categorized.keys()):
        body += f"<h3>🔹 {kw}</h3>\n<ul>\n"
        for dt, title, link in categorized[kw]:
            body += f"<li>[{dt}] <a href='{link}' target='_blank'>{title}</a></li>\n"
        body += "</ul>\n"

    body += "<hr><p style='font-size:small;color:gray;'>Email generado automáticamente</p>"
    return body
    
def send_email(html_body, subject):
    SENDER = os.getenv("SENDER_EMAIL")
    PASS   = os.getenv("SENDER_PASSWORD")
    TO     = os.getenv("RECIPIENT_EMAIL")

    for var in ("SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL"):
        if not os.getenv(var):
            print(f"❌ Missing {var}", file=sys.stderr)
            sys.exit(1)

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = TO

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(SENDER, PASS)
            s.send_message(msg)
        print("✅ Summary email sent!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    print("🚀 Starting process...")

    # Download and delete artifacts
    fetch_and_process_artifacts()

    # Load and merge data
    merged = load_and_merge(artifact_dir)
    if not merged:
        print("ℹ️ No new news items to send.")
        return

    # Build email and send it
    body = build_email_body(merged)
    subject = f"Daily Interests {datetime.now().strftime('%d/%m/%Y')}"
    send_email(body, subject)

if __name__ == "__main__":
    main()
