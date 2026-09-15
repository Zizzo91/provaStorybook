#!/usr/bin/env python3
"""Seed per la webapp Storybook (schema `storybook` su Supabase).

Uso (usa la service_role key SOLO qui, mai nel frontend):
  python3 script/seed_supabase.py [/path/supabase-secrets.json] [--groq-key KEY] [--dry-run]

- scrive la Groq API key in storybook.settings (per l'utente pinEmail)
- importa le storie da stories/*.json in storybook.stories

La Groq key viene presa da --groq-key oppure letta da settings/config.json
(locale, gitignored / backup). Se assente, scrive comunque le storie.
"""
import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN_EMAIL = "simone.marramao@hotmail.it"
SCHEMA = "storybook"


def request(svc_url, key, path, body=None, schema=None):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    sch = schema or SCHEMA
    headers["Accept-Profile"] = sch
    if body is not None:
        headers["Content-Profile"] = sch
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        svc_url.rstrip("/") + path,
        data=data,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{path} -> {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from e


def get_groq_key(args_groq, settings_cfg_abs):
    if args_groq:
        return args_groq
    if settings_cfg_abs and os.path.exists(settings_cfg_abs):
        try:
            return json.load(open(settings_cfg_abs)).get("groq", "")
        except Exception:
            return ""
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("secrets", nargs="?", help="percorso supabase-secrets.json")
    ap.add_argument("--groq-key", default="", help="Groq API key (altrimenti letta da settings/config.json locale)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    secrets = args.secrets or os.path.join(os.path.dirname(BASE), "Config Utility", "supabase-secrets.json")
    with open(secrets) as f:
        s = json.load(f)
    svc_url = s["project_url"]
    key = s["service_role_key_secret"]

    cfg = os.path.join(BASE, "settings", "config.json")
    groq_key = get_groq_key(args.groq_key, cfg)

    # risolvi user_id via public.profiles
    st, body = request(svc_url, key, f"/rest/v1/profiles?select=id&email=eq.{urllib.parse.quote(PIN_EMAIL)}", schema="public")
    profiles = json.loads(body)
    if not profiles:
        print(f"ERRORE: nessun profilo per {PIN_EMAIL} (fai un primo login PIN nella webapp).")
        return 1
    user_id = profiles[0]["id"]
    print(f"user_id risolto: {user_id} ({PIN_EMAIL})")

    stories = []
    for fp in sorted(glob.glob(os.path.join(BASE, "stories", "*.json"))):
        with open(fp) as f:
            d = json.load(f)
        slug = (d.get("title") or "storia-senza-titolo").lower().replace(" ", "-")
        stories.append({
            "user_id": user_id,
            "slug": slug,
            "title": d.get("title", ""),
            "audience": d.get("audience", ""),
            "tone": d.get("tone", ""),
            "idea": d.get("idea", ""),
            "short_version": d.get("shortVersion", ""),
            "chapters": d.get("chapters", []),
        })
    print(f"storie da importare: {len(stories)}")

    if args.dry_run:
        print("DRY-RUN: nessuna scrittura.")
        return 0

    settings_rows = []
    if groq_key:
        settings_rows.append({"user_id": user_id, "groq_api_key": groq_key})
    else:
        print("ATTENZIONE: nessuna Groq key disponibile, si salta storybook.settings.")
    if settings_rows:
        st, body = request(svc_url, key, f"/rest/v1/settings?on_conflict=user_id", settings_rows)
        print("settings upsert:", st, body[:200])

    if stories:
        st, body = request(svc_url, key, f"/rest/v1/stories?on_conflict=user_id,slug", stories)
        print("stories upsert:", st, body[:200])

    return 0


if __name__ == "__main__":
    sys.exit(main())