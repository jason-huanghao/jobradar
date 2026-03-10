"""Interactive setup wizard — writes config.yaml and .env in one shot.

Run via: jobradar --setup
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Provider presets ───────────────────────────────────────────────

PROVIDERS = [
    {
        "name": "Volcengine Ark",
        "desc": "doubao-seed series — recommended for CN users",
        "provider": "volcengine",
        "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "model": "doubao-seed-2.0-code",
        "env_var": "ARK_API_KEY",
        "needs_key": True,
    },
    {
        "name": "Z.AI",
        "desc": "Z.AI coding plan",
        "provider": "zai",
        "base_url": "https://api.z.ai/v1",
        "model": "claude-sonnet-4-20250514",
        "env_var": "ZAI_API_KEY",
        "needs_key": True,
    },
    {
        "name": "DeepSeek",
        "desc": "~$0.14/1M tokens, strong reasoning",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "env_var": "DEEPSEEK_API_KEY",
        "needs_key": True,
    },
    {
        "name": "OpenAI",
        "desc": "GPT-4o-mini recommended for cost",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "env_var": "OPENAI_API_KEY",
        "needs_key": True,
    },
    {
        "name": "OpenRouter",
        "desc": "200+ models via one key — openrouter.ai",
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3-5-haiku",
        "env_var": "OPENROUTER_API_KEY",
        "needs_key": True,
    },
    {
        "name": "LM Studio",
        "desc": "Local models via lmstudio.ai — free, no API key needed",
        "provider": "lm_studio",
        "base_url": "http://localhost:1234/v1",
        "model": "",        # auto-detected from running server
        "env_var": "",
        "needs_key": False,
    },
    {
        "name": "Ollama",
        "desc": "Local models, free, no API key needed",
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "env_var": "",
        "needs_key": False,
    },
    {
        "name": "Other",
        "desc": "Any OpenAI-compatible endpoint",
        "provider": "custom",
        "base_url": "",
        "model": "",
        "env_var": "LLM_API_KEY",
        "needs_key": True,
    },
]


def _prompt(msg: str, default: str = "") -> str:
    """Prompt user for input, returning default on empty enter."""
    if default:
        display = f"{msg} [{default}]: "
    else:
        display = f"{msg}: "
    try:
        val = input(display).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(0)


def _pick_provider() -> dict:
    print("\n  LLM Provider:")
    for i, p in enumerate(PROVIDERS, 1):
        print(f"    {i}. {p['name']:<20} {p['desc']}")
    while True:
        choice = _prompt("\n  Choose provider", "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(PROVIDERS):
                return PROVIDERS[idx]
        except ValueError:
            pass
        print("  Invalid choice, try again.")


def run_setup(project_root: Path) -> None:
    """Interactive wizard — writes config.yaml and .env."""
    print("\n🤖  JobRadar Setup Wizard")
    print("─" * 40)

    # ── Step 1: LLM Provider ──
    print("\nStep 1/5 — LLM Provider")
    provider = _pick_provider()

    api_key = ""
    if provider["needs_key"]:
        print(f"\nStep 2/5 — API Key for {provider['name']}")
        print("  (saved to .env, never committed to git)")
        api_key = _prompt("  Paste your API key")
        if not api_key:
            print("  ⚠️  No API key entered — you can add it to .env later.")

    # Custom provider details
    base_url = provider["base_url"]
    model = provider["model"]
    if provider["provider"] == "custom":
        print("\n  Custom provider details:")
        base_url = _prompt("  Base URL (e.g. http://localhost:8000/v1)", "http://localhost:8000/v1")
        model = _prompt("  Model name", "gpt-4o")

    # ── Step 3: CV path ──
    print("\nStep 3/5 — CV File Path (Markdown format)")
    default_cv = "./cv/cv_current.md"
    cv_path = _prompt("  CV path", default_cv)

    # ── Step 4: Locations ──
    print("\nStep 4/5 — Target Locations (comma-separated)")
    locs_raw = _prompt("  Locations", "Germany, Remote")
    locations = [loc.strip() for loc in locs_raw.split(",") if loc.strip()]

    # ── Step 5: Email notifications (optional) ──
    print("\nStep 5/5 — Email Notifications (optional, press Enter to skip)")
    email_enabled = _prompt("  Enable email digest? (y/n)", "n").lower() == "y"
    email_addr = ""
    smtp_host = "smtp.gmail.com"
    if email_enabled:
        email_addr = _prompt("  Your email address")
        smtp_host = _prompt("  SMTP host", "smtp.gmail.com")

    # ── Write .env ──
    env_path = project_root / ".env"
    env_lines: list[str] = ["# JobRadar environment variables — do not commit to git\n"]
    if provider["needs_key"] and provider["env_var"] and api_key:
        env_lines.append(f"{provider['env_var']}={api_key}\n")
    if email_enabled and email_addr:
        env_lines.append("# For Gmail: generate an App Password at myaccount.google.com/apppasswords\n")
        env_lines.append("GMAIL_APP_PASSWORD=\n")
    env_path.write_text("".join(env_lines), encoding="utf-8")

    # ── Write config.yaml ──
    locations_yaml = "\n".join(f"    - \"{loc}\"" for loc in locations)
    email_section = ""
    if email_enabled:
        email_section = f"""
notifications:
  email:
    enabled: true
    smtp_host: {smtp_host}
    smtp_port: 587
    from_addr: {email_addr}
    to_addr: {email_addr}
    app_password_env: GMAIL_APP_PASSWORD
    min_score_to_notify: 7
    max_jobs_in_email: 10
"""
    else:
        email_section = """
notifications:
  email:
    enabled: false
"""

    config_content = f"""# JobRadar configuration — generated by setup wizard
# Edit freely. Re-run 'jobradar --setup' to regenerate.

candidate:
  cv_path: "{cv_path}"
  profile_path: "./cv/profile.md"
  profile_json_path: ""

llm:
  text:
    provider: "{provider['provider']}"
    model: "{model}"
    base_url: "{base_url}"
    api_key_env: "{provider['env_var']}"
    temperature: 0.3
    max_tokens: 4096

search:
  locations:
{locations_yaml}
  radius_km: 50
  postal_code: "30159"
  max_results_per_source: 50
  max_days_old: 14
  job_types:
    - "fulltime"
  custom_keywords: []

sources:
  arbeitsagentur:
    enabled: true
  jobspy:
    enabled: true
    boards:
      - "indeed"
      - "google"
    country: "germany"
  stepstone:
    enabled: false
  linkedin:
    enabled: false
  xing:
    enabled: false

scoring:
  min_score_digest: 6
  min_score_application: 7
  batch_size: 5

output:
  dir: "./outputs"
  excel:
    enabled: true
    filename: "jobs_pipeline.xlsx"
  digest:
    enabled: true
    dir: "digests"
  applications:
    enabled: true
    dir: "applications"

runtime:
  mode: "full"
  log_level: "INFO"
  cache_dir: "./memory"
  skip_unchanged_cv: true
{email_section}
web:
  enabled: false
  host: "0.0.0.0"
  port: 8000
"""

    config_path = project_root / "config.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    # ── Done ──
    print("\n" + "─" * 40)
    print("✅  config.yaml written")
    print("✅  .env written")
    print()
    print("  Next steps:")
    print("    jobradar --mode quick    # fast test (2 sources, ~3 min)")
    print("    jobradar                 # full pipeline")
    print("    jobradar --install-agent # set up daily 8am automation")
    print()
