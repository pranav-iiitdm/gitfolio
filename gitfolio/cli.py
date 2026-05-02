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
def sync(backfill, dry_run):
    """Fetch commits, generate bullets, update resume, send digest email."""
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


def main():
    cli()
