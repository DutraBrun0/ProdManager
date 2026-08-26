from werkzeug.security import check_password_hash

from models import Usuario


def test_cadastro_publico_cria_cliente(client):
    resposta = client.post(
        "/cliente/register",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@teste.com",
            "senha": "senha123"
        }
    )

    dados = resposta.get_json()

    assert resposta.status_code == 201
    assert dados["status"] == "ok"

    cliente = Usuario.query.filter_by(
        email="cliente@teste.com"
    ).first()

    assert cliente is not None
    assert cliente.perfil == "cliente"
    assert check_password_hash(
        cliente.senha_hash,
        "senha123"
    )


def test_cadastro_rejeita_email_duplicado(client):
    cliente = {
        "nome": "Cliente Teste",
        "email": "cliente@teste.com",
        "senha": "senha123"
    }

    primeira_resposta = client.post(
        "/cliente/register",
        json=cliente
    )

    segunda_resposta = client.post(
        "/cliente/register",
        json=cliente
    )

    dados = segunda_resposta.get_json()

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 400
    assert dados["status"] == "erro"
    assert dados["mensagem"] == "E-mail já cadastrado"


def test_login_com_dados_corretos(
    client,
    criar_usuario
):
    usuario = criar_usuario(
        email="login@teste.com",
        senha="senha123",
        perfil="admin"
    )

    resposta = client.post(
        "/login",
        json={
            "email": "login@teste.com",
            "senha": "senha123"
        }
    )

    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["status"] == "ok"

    with client.session_transaction() as sessao:
        assert sessao["user_id"] == usuario.id
        assert sessao["user_perfil"] == "admin"


def test_login_rejeita_senha_incorreta(
    client,
    criar_usuario
):
    criar_usuario(
        email="login@teste.com",
        senha="senha123"
    )

    resposta = client.post(
        "/login",
        json={
            "email": "login@teste.com",
            "senha": "senha-errada"
        }
    )

    dados = resposta.get_json()

    assert resposta.status_code == 401
    assert dados["status"] == "erro"
    assert dados["mensagem"] == "E-mail ou senha inválidos"


def test_inicio_redireciona_usuario_sem_login(client):
    resposta = client.get(
        "/inicio",
        follow_redirects=False
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/")


def test_login_rejeita_usuario_inativo(
    client,
    criar_usuario
):
    criar_usuario(
        email="inativo@teste.com",
        senha="senha123",
        ativo=False
    )

    resposta = client.post(
        "/login",
        json={
            "email": "inativo@teste.com",
            "senha": "senha123"
        }
    )

    dados = resposta.get_json()

    assert resposta.status_code == 401
    assert dados["status"] == "erro"
    assert dados["mensagem"] == "E-mail ou senha inválidos"

def test_login_configura_cookie_seguro(
    client,
    criar_usuario
):
    criar_usuario(
        email="cookie@teste.com",
        senha="senha123"
    )

    resposta = client.post(
        "/login",
        json={
            "email": "cookie@teste.com",
            "senha": "senha123"
        }
    )

    cookie = resposta.headers.get("Set-Cookie")

    assert resposta.status_code == 200
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_resposta_possui_cabecalhos_de_seguranca(
    client
):
    resposta = client.get("/")

    assert (
        resposta.headers["X-Content-Type-Options"]
        == "nosniff"
    )

    assert resposta.headers["X-Frame-Options"] == "DENY"

    assert (
        resposta.headers["Referrer-Policy"]
        == "strict-origin-when-cross-origin"
    )