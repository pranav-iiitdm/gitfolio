from flask import Flask, jsonify, request, render_template
from gitfolio.pending_store import PendingStore


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/bullets")
    def get_bullets():
        store = PendingStore()
        return jsonify(store.load())

    @app.patch("/api/bullets/<bullet_id>")
    def update_bullet(bullet_id: str):
        data = request.get_json(force=True) or {}
        store = PendingStore()
        updated = store.update(
            bullet_id,
            status=data.get("status"),
            bullet_text=data.get("bullet"),
        )
        if not updated:
            return jsonify({"error": "not found"}), 404
        return jsonify({"ok": True})

    @app.post("/api/push")
    def push():
        store = PendingStore()
        approved = store.get_approved()
        if not approved:
            return jsonify({"error": "no approved bullets"}), 400

        try:
            from gitfolio.config import Config
            from gitfolio.resume_updater import ResumeUpdater
            from gitfolio.emailer import Emailer

            config = Config.load()
            updater = ResumeUpdater(config)
            updated_tex, diff_summary = updater.inject(approved)

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
            return jsonify({"ok": True, "injected": len(approved)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app
