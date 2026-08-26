import os
import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["FLASK_SECRET_KEY"] = "chave-exclusiva-dos-testes"
os.environ["FLASK_DEBUG"] = "false"


from app import app as flask_app
from database import db
from models import Usuario


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.create_all()

        yield flask_app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def criar_usuario(app):
    def _criar_usuario(
        nome="Usuário Teste",
        email="usuario@teste.com",
        senha="senha123",
        perfil="cliente",
        ativo=True
    ):
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(senha),
            perfil=perfil,
            ativo=ativo
        )

        db.session.add(usuario)
        db.session.commit()

        return usuario

    return _criar_usuario


@pytest.fixture()
def autenticar(client):
    def _autenticar(usuario):
        with client.session_transaction() as sessao:
            sessao["user_id"] = usuario.id
            sessao["user_nome"] = usuario.nome
            sessao["user_email"] = usuario.email
            sessao["user_perfil"] = usuario.perfil

    return _autenticar