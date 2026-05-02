import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


class Emailer:
    def __init__(self, config: dict):
        self.email_from = config["email_from"]
        self.email_password = config["email_password"]
        self.email_to = config["email_to"]

    def send(
        self,
        updated_tex: str,
        tier1: list[dict],
        tier2: list[dict],
        tier3: list[dict],
        diff_summary: str,
    ):
        date_str = datetime.now().strftime("%B %d, %Y")
        subject = f"gitfolio weekly digest — {date_str}"

        body = self._build_body(tier1, tier2, tier3, diff_summary, date_str)

        msg = MIMEMultipart()
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # Attach updated .tex file
        tex_filename = f"resume_updated_{datetime.now().strftime('%Y%m%d')}.tex"
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(updated_tex.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={tex_filename}"
        )
        msg.attach(attachment)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.email_from, self.email_password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())

    def _build_body(
        self,
        tier1: list,
        tier2: list,
        tier3: list,
        diff_summary: str,
        date_str: str,
    ) -> str:
        lines = [
            f"gitfolio weekly digest — {date_str}",
            "=" * 50,
            "",
            "Here's what happened in your repos this week.",
            "",
            "SUMMARY",
            "-------",
            diff_summary,
        ]

        if tier2:
            lines += [
                "ACTION NEEDED",
                "-------------",
                "These bullets need a metric from you.",
                "Reply with the numbers and I'll include them next week.",
                "",
            ]
            for r in tier2:
                lines.append(f"  Bullet: {r['bullet']}")
                if r.get("flag_reason"):
                    lines.append(f"  Question: {r['flag_reason']}")
                lines.append("")

        if tier3:
            lines += [
                f"SKIPPED ({len(tier3)} items)",
                "-------",
                "These were too small to include:",
            ]
            for r in tier3:
                title = r.get("cluster", {}).get("pr_title", "unknown")
                lines.append(f"  • {title}")
            lines.append("")

        lines += [
            "=" * 50,
            "The updated resume .tex file is attached.",
            "Review it, upload to Overleaf, and you're done.",
            "",
            "— gitfolio",
        ]

        return "\n".join(lines)
