def test_api_exige_autenticacao(client):
    resposta = client.get("/api/clientes")
    dados = resposta.get_json()

    assert resposta.status_code == 401
    assert dados["status"] == "erro"
    assert dados["mensagem"] == "Autenticação necessária"


def test_cliente_nao_acessa_estoque(
    client,
    criar_usuario,
    autenticar
):
    cliente = criar_usuario(
        perfil="cliente"
    )

    autenticar(cliente)

    resposta = client.get("/estoque")

    assert resposta.status_code == 403


def test_cliente_nao_movimenta_estoque(
    client,
    criar_usuario,
    autenticar
):
    cliente = criar_usuario(
        perfil="cliente"
    )

    autenticar(cliente)

    resposta = client.post(
        "/estoque/entrada_sku",
        json={
            "variante_id": 1,
            "quantidade": 10
        }
    )

    assert resposta.status_code == 403


def test_usuario_estoque_acessa_estoque(
    client,
    criar_usuario,
    autenticar
):
    usuario = criar_usuario(
        perfil="estoque"
    )

    autenticar(usuario)

    resposta = client.get("/estoque")

    assert resposta.status_code == 200


def test_usuario_estoque_nao_acessa_faturamento(
    client,
    criar_usuario,
    autenticar
):
    usuario = criar_usuario(
        perfil="estoque"
    )

    autenticar(usuario)

    resposta = client.get("/faturamento")

    assert resposta.status_code == 403


def test_admin_acessa_cadastro_de_usuarios(
    client,
    criar_usuario,
    autenticar
):
    administrador = criar_usuario(
        perfil="admin"
    )

    autenticar(administrador)

    resposta = client.get("/register_page")

    assert resposta.status_code == 200
