import click
from flask import Flask
from flask_cors import CORS

from config import Config
from .errors import register_error_handlers
from .extensions import db, migrate


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    register_error_handlers(app)

    from . import models  # noqa: F401
    from .routes import api
    app.register_blueprint(api)
    from .metrics import init_metrics
    init_metrics(app)

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete all existing data first")
    def seed_cmd(reset):
        """Load clearly-labelled [DEMO] data."""
        from .seed import seed
        click.echo(seed(reset))

    return app
