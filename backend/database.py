import os
from urllib.parse import quote_plus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_app(app: Flask):
    usuario = os.getenv("DB_USER")
    senha = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "3306")
    banco = os.getenv("DB_NAME")

    if not usuario or not senha or not banco:
        raise RuntimeError(
            "Configurações do banco não encontradas no arquivo .env"
        )

    senha_protegida = quote_plus(senha)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{usuario}:{senha_protegida}"
        f"@{host}:{porta}/{banco}?charset=utf8mb4"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)