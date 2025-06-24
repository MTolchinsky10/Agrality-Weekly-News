#!/usr/bin/env python3
import argparse
import feedparser
import json
import os
import sys
import time
import unicodedata
import re
from datetime import datetime, timedelta

import os

def load_keywords_from_env() -> list[str]:
    raw = os.getenv("KEYWORDS", "")
    return [k.strip().lower() for k in raw.split(",") if k.strip()]

KEYWORDS = load_keywords_from_env()

# You can add as many RSS links as you want provided that said news coverage site has RSS links available
RSS_FEEDS = [
# LA NACION
    "https://www.lanacion.com.ar/arc/outboundfeeds/rss/",
# CLARIN
    "https://www.clarin.com/rss/mundo/",
    "https://www.clarin.com/rss/sociedad/",
    "https://www.clarin.com/rss/policiales/",
    "https://www.clarin.com/rss/ciudades/",
    "https://www.clarin.com/rss/opinion/",
    "https://www.clarin.com/rss/cartas_al_pais/",
    "https://www.clarin.com/rss/cultura/",
    "https://www.clarin.com/rss/rural/",
    "https://www.clarin.com/rss/economia/",
    "https://www.clarin.com/rss/tecnologia/",
    "https://www.clarin.com/rss/internacional/",
    "https://www.clarin.com/rss/revista-enie/",
    "https://www.clarin.com/rss/viva/",
    "https://www.clarin.com/rss/br/",
    "https://www.clarin.com/rss/deportes/",
    "https://www.clarin.com/rss/espectaculos/tv/",
    "https://www.clarin.com/rss/espectaculos/cine/",
    "https://www.clarin.com/rss/espectaculos/musica/",
    "https://www.clarin.com/rss/espectaculos/teatro/",
    "https://www.clarin.com/rss/espectaculos/",
    "https://www.clarin.com/rss/autos/",
    "https://www.clarin.com/rss/buena-vida/",
    "https://www.clarin.com/rss/viajes/",
    "https://www.clarin.com/rss/arq/",
# INFOCAMPO
    "https://www.infocampo.com.ar/feed/",
# BICHOS DE CAMPO
    "https://www.infocampo.com.ar/feed/",
# VALOR SOJA
    "https://www.valorsoja.com/feed/",
# TODO AGRO
    "https://www.todoagro.com.ar/feed/",
# SUPER CAMPO
    "https://supercampo.perfil.com/feed/",
# PERFIL
    "https://www.perfil.com/feed",
    "https://www.perfil.com/rss/politica",
    "https://www.perfil.com/rss/economia",
    "https://www.perfil.com/rss/sociedad",
    "https://www.perfil.com/rss/deportes",
    "https://www.perfil.com/rss/internacional",
    "https://www.perfil.com/rss/espectaculos",
    "https://www.perfil.com/rss/cultura",
    "https://www.perfil.com/rss/tecnologia",
    "https://www.perfil.com/rss/salud",
    "https://www.perfil.com/rss/agro",
    "https://www.perfil.com/rss/autos",
# INFOBAE
    "https://www.infobae.com/arc/outboundfeeds/rss/",
# SEED TODAY
    "https://www.seedtoday.com/rss.xml"
]

def normalize_text(text: str) -> str:
    nk = unicodedata.normalize('NFKD', text)
    return nk.encode('ascii', 'ignore').decode('ascii').lower()

timestamp = datetime.utcnow().strftime("%Y_%m_%d__%H_%M_%S")

def parse_args():
    p = argparse.ArgumentParser(description="Fetch multiple RSS feeds, filter by keywords & date, emit JSON.")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--since-days", type=int, default=1, help="How many days back to include (default 1).")
    group.add_argument("--since-hours", type=float, help="How many hours back to include (overrides --since-days).")
    p.add_argument("--output", default=f"RSS_FEEDS_{timestamp}.json", help="Path to write raw JSON.")
    return p.parse_args()

def main():
    args = parse_args()
    now = datetime.utcnow()

    if args.since_hours is not None:
        start_date = now - timedelta(hours=args.since_hours)
    else:
        start_date = now - timedelta(days=args.since_days)
    end_date = now

    print(f"⏱ Filtrando entradas desde {start_date.isoformat()} hasta {end_date.isoformat()}\n")

    grouped_news = {}

    for feed_url in RSS_FEEDS:
        print(f"🌐 Procesando feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        source_title = feed.feed.get("title", "Fuente desconocida")
        print(f"📄 Fuente detectada: {source_title} | Entradas: {len(feed.entries)}")

        for entry in feed.entries:
            try:
                published_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except AttributeError:
                continue

            if not (start_date <= published_time <= end_date):
                continue

            title = entry.get("title", "")

            content = ""
            if "content" in entry and entry.content:
                content = entry.content[0].value
            elif "content:encoded" in entry:
                content = entry["content:encoded"]
            elif "description" in entry:
                content = entry["description"]
            elif "summary" in entry:
                content = entry["summary"]

            content_to_check = normalize_text(title + " " + content)

            matched_keywords = [
                k for k in KEYWORDS
                if re.search(r'\b{}\b'.format(re.escape(normalize_text(k))), content_to_check)
            ]

            if matched_keywords:
                print(f"✅ MATCH: {title[:80]}...")
                print(f"   🗝️ Keywords: {matched_keywords}")
                grouped_news.setdefault(source_title, []).append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": published_time.isoformat(),
                    "matched_keywords": matched_keywords
                })

        print("")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(grouped_news, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in grouped_news.values())
    print(f"✅ Total de noticias capturadas: {total}")
    print(f"📁 Archivo guardado: {args.output}")

if __name__ == "__main__":
    main()
