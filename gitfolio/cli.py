import click
import os
from gitfolio.github_analyzer import GitHubAnalyzer
from gitfolio.bullet_generator import BulletGenerator
from gitfolio.resume_updater import ResumeUpdater
from gitfolio.emailer import Emailer
from gitfolio.config import Config

@click.group()
def cli():
    """gitfolio — auto-generate resume bullets from your GitHub commits."""
    pass

@cli.command()
def init():
    """Interactive setup: GitHub token, repos, email, resume path."""
    click.echo("\n🚀 Welcome to gitfolio setup\n")

    token = click.prompt("GitHub Personal Access Token (needs repo scope)")
    repos = click.prompt("Repos to scan (comma-separated, e.g. org/repo1,org/repo2)")
    email_from = click.prompt("Your Gmail address (for sending digest)")
    email_pass = click.prompt("Gmail App Password", hide_input=True)
    email_to = click.prompt("Send digest to (your email)")
    resume_path = click.prompt("Path to your .tex resume file")
    target_role = click.prompt("Target role (e.g. SDE, Backend Engineer)")
    author_email = click.prompt("Git author email (used to filter your commits)")

    diff_access_input = click.prompt(
        "Allow sending code diffs to Claude? (yes/no, 'no' uses only PR titles)",
        default="yes"
    )

    config = {
        "github_token": token,
        "repos": [r.strip() for r in repos.split(",")],
        "email_from": email_from,
        "email_password": email_pass,
        "email_to": email_to,
        "resume_path": resume_path,
        "target_role": target_role,
        "author_email": author_email,
        "diff_access": diff_access_input.lower() != "no",
    }

    Config.save(config)
    click.echo("\n✅ Config saved to config.yaml")
    click.echo("Run `gitfolio sync --backfill` to do your first full scan.\n")


@cli.command()
@click.option("--backfill", is_flag=True, help="Scan last 12 months instead of last 7 days.")
@click.option("--dry-run", is_flag=True, help="Preview bullets without updating resume or sending email.")
@click.option("--auto", is_flag=True, help="Generate, inject, and email in one shot (use in cron).")
def sync(backfill, dry_run, auto):
    """Fetch commits, generate bullets, save to pending (or --auto to inject immediately)."""
    from gitfolio.pending_store import PendingStore
    config = Config.load()

    click.echo("\n🔍 Fetching GitHub activity...")
    analyzer = GitHubAnalyzer(config)
    clusters = analyzer.fetch(backfill=backfill)
    click.echo(f"   Found {len(clusters)} PR/commit clusters")

    click.echo("🤖 Generating resume bullets via Claude...")
    generator = BulletGenerator(config)
    results = generator.generate(clusters)

    tier1 = [r for r in results if r["tier"] == 1]
    tier2 = [r for r in results if r["tier"] == 2]
    tier3 = [r for r in results if r["tier"] == 3]

    click.echo(f"   Tier 1 (auto-include): {len(tier1)}")
    click.echo(f"   Tier 2 (needs metric): {len(tier2)}")
    click.echo(f"   Tier 3 (skipped): {len(tier3)}")

    if dry_run:
        click.echo("\n📋 Dry run — proposed bullets:\n")
        for r in tier1 + tier2:
            flag = "⚠️ " if r["tier"] == 2 else "✅ "
            click.echo(f"{flag}{r['bullet']}")
            if r.get("flag_reason"):
                click.echo(f"   → {r['flag_reason']}")
        click.echo("\nDry run complete. No files modified, no email sent.\n")
        return

    if auto:
        click.echo("📝 Updating resume...")
        updater = ResumeUpdater(config)
        updated_tex, diff_summary = updater.inject(tier1 + tier2)

        click.echo("📧 Sending digest email...")
        emailer = Emailer(config)
        emailer.send(
            updated_tex=updated_tex,
            tier1=tier1,
            tier2=tier2,
            tier3=tier3,
            diff_summary=diff_summary,
        )
        Config.update_last_sync()
        click.echo("\n✅ Done! Check your inbox for the digest + updated .tex file.\n")
    else:
        store = PendingStore()
        store.save(results)
        actionable = len(tier1) + len(tier2)
        click.echo(f"\n📋 {actionable} bullet(s) saved to pending.")
        click.echo("Run `gitfolio review` or `gitfolio serve` to review them.\n")


@cli.command()
def doctor():
    """Check config, GitHub connection, and Claude API access."""
    click.echo("\n🩺 Running gitfolio diagnostics...\n")
    config = Config.load()

    # GitHub check
    try:
        from github import Github
        g = Github(config["github_token"])
        user = g.get_user()
        click.echo(f"✅ GitHub connected as: {user.login}")
    except Exception as e:
        click.echo(f"❌ GitHub connection failed: {e}")

    # Anthropic check
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        click.echo("✅ Anthropic API key found")
    except Exception as e:
        click.echo(f"❌ Anthropic API issue: {e}")

    if "anthropic_api_key" in config:
        click.echo("⚠️  ANTHROPIC_API_KEY found in config.yaml — remove it and use env var instead")

    # Resume file check
    resume_path = config.get("resume_path", "")
    if os.path.exists(resume_path):
        click.echo(f"✅ Resume found: {resume_path}")
    else:
        click.echo(f"❌ Resume not found at: {resume_path}")

    # Last sync
    last_sync = Config.get_last_sync()
    if last_sync:
        click.echo(f"✅ Last sync: {last_sync}")
    else:
        click.echo("ℹ️  No sync run yet — run `gitfolio sync --backfill` first")

    click.echo("")


def _show_bullet(bullet: dict, idx: int, total: int) -> None:
    cluster = bullet.get("cluster", {})
    click.echo("─" * 52)
    click.echo(f"[{idx}/{total}] {cluster.get('repo', 'unknown')} · {cluster.get('work_type', '?')} · score {bullet.get('score', 0):.0f}")
    click.echo(f"PR: {cluster.get('pr_title', '')}\n")
    click.echo(f"  {bullet.get('bullet', '')}\n")
    if bullet.get("keywords"):
        click.echo(f"  Keywords: {', '.join(bullet['keywords'])}")
    if bullet.get("tier") == 2 and bullet.get("flag_reason"):
        click.echo(f"  ⚠️  Tier 2 — {bullet['flag_reason']}")
    click.echo("\n[a]pprove  [e]dit  [s]kip  [d]elete  [q]uit")
    click.echo("─" * 52)


@cli.command()
@click.option("--push", "do_push", is_flag=True, help="Inject approved bullets and send email after review.")
def review(do_push):
    """Review pending bullets: approve, edit, skip, or delete."""
    from gitfolio.pending_store import PendingStore
    store = PendingStore()
    bullets = [b for b in store.load() if b["status"] == "pending"]

    if not bullets:
        click.echo("\nNo pending bullets to review. Run `gitfolio sync` first.\n")
        return

    total = len(bullets)
    for i, bullet in enumerate(bullets):
        click.clear()
        _show_bullet(bullet, i + 1, total)
        while True:
            choice = click.getchar().lower()
            if choice == "a":
                store.update(bullet["id"], status="approved")
                click.echo("\n✅ Approved")
                break
            elif choice == "e":
                edited = click.edit(bullet.get("bullet", ""))
                if edited and edited.strip():
                    store.update(bullet["id"], status="approved", bullet_text=edited.strip())
                    click.echo("\n✅ Edited and approved")
                else:
                    store.update(bullet["id"], status="approved")
                    click.echo("\n✅ Approved (no edits)")
                break
            elif choice == "s":
                click.echo("\n⏭  Skipped")
                break
            elif choice == "d":
                store.update(bullet["id"], status="deleted")
                click.echo("\n🗑  Deleted")
                break
            elif choice == "q":
                click.echo("\nReview paused. Run `gitfolio review` to continue.\n")
                return

    approved_count = len(store.get_approved())
    click.echo(f"\nReview complete. {approved_count} bullet(s) approved.")
    if approved_count == 0:
        return
    if do_push:
        ctx = click.get_current_context()
        ctx.invoke(push_cmd)
    else:
        click.echo("Run `gitfolio push` to inject them into your resume.\n")


@cli.command(name="push")
def push_cmd():
    """Inject approved bullets into resume and send digest email."""
    from gitfolio.pending_store import PendingStore
    config = Config.load()
    store = PendingStore()
    approved = store.get_approved()

    if not approved:
        click.echo("\nNo approved bullets to push. Run `gitfolio review` first.\n")
        return

    click.echo(f"\n📝 Injecting {len(approved)} approved bullet(s) into resume...")
    updater = ResumeUpdater(config)
    updated_tex, diff_summary = updater.inject(approved)

    click.echo("📧 Sending digest email...")
    emailer = Emailer(config)
    all_bullets = store.load()
    tier1 = [b for b in approved if b.get("tier") == 1]
    tier2 = [b for b in approved if b.get("tier") == 2]
    tier3 = [b for b in all_bullets if b.get("tier") == 3 or b.get("status") == "deleted"]
    emailer.send(
        updated_tex=updated_tex,
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        diff_summary=diff_summary,
    )

    store.clear()
    Config.update_last_sync()
    click.echo("\n✅ Done! Check your inbox for the digest + updated .tex file.\n")


@cli.command()
@click.option("--port", default=7842, show_default=True, help="Port for the web UI.")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically.")
def serve(port, no_browser):
    """Start local web UI for reviewing bullets at localhost:<port>."""
    import webbrowser
    from gitfolio.server import create_app

    url = f"http://localhost:{port}"
    click.echo(f"\n🌐 Starting gitfolio web UI at {url}")
    click.echo("Press Ctrl+C to stop.\n")

    if not no_browser:
        webbrowser.open(url)

    app = create_app()
    app.run(host="127.0.0.1", port=port, debug=False)


def main():
    cli()
