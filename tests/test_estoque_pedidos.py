from decimal import Decimal

from database import db
from models import (
    Estoque,
    MovimentoEstoque,
    Pedido,
    Produto,
    Variante
)


def criar_produto_com_estoque(
    quantidade=10,
    preco="150.00"
):
    produto = Produto(
        linha="Linha Teste",
        formato="Retangular",
        descricao="Produto utilizado nos testes"
    )

    db.session.add(produto)
    db.session.flush()

    variante = Variante(
        produto_id=produto.id,
        altura_cm=100,
        largura_cm=80,
        cor="Preto",
        moldura="Alumínio",
        sku="TESTE-100-80-PRETO",
        preco_base=Decimal(preco),
        ativo=True
    )

    db.session.add(variante)
    db.session.flush()

    estoque = Estoque(
        variante_id=variante.id,
        quantidade=quantidade,
        minimo=2
    )

    db.session.add(estoque)
    db.session.commit()

    return produto, variante, estoque


def test_entrada_aumenta_estoque(
    client,
    criar_usuario,
    autenticar
):
    administrador = criar_usuario(
        email="admin@teste.com",
        perfil="admin"
    )

    autenticar(administrador)

    _, variante, estoque = criar_produto_com_estoque(
        quantidade=5
    )

    resposta = client.post(
        "/estoque/entrada_sku",
        json={
            "variante_id": variante.id,
            "quantidade": 3,
            "motivo": "Entrada de teste"
        }
    )

    dados = resposta.get_json()

    db.session.refresh(estoque)

    assert resposta.status_code == 200
    assert dados["status"] == "ok"
    assert dados["estoque_atual"] == 8
    assert estoque.quantidade == 8
    assert MovimentoEstoque.query.count() == 1


def test_saida_nao_permite_estoque_negativo(
    client,
    criar_usuario,
    autenticar
):
    administrador = criar_usuario(
        email="admin@teste.com",
        perfil="admin"
    )

    autenticar(administrador)

    _, variante, estoque = criar_produto_com_estoque(
        quantidade=2
    )

    resposta = client.post(
        "/estoque/saida_sku",
        json={
            "variante_id": variante.id,
            "quantidade": 3,
            "motivo": "Saída de teste"
        }
    )

    dados = resposta.get_json()

    db.session.refresh(estoque)

    assert resposta.status_code == 400
    assert dados["status"] == "erro"
    assert estoque.quantidade == 2
    assert MovimentoEstoque.query.count() == 0


def test_criar_pedido_reduz_estoque(
    client,
    criar_usuario,
    autenticar
):
    administrador = criar_usuario(
        email="admin@teste.com",
        perfil="admin"
    )

    cliente = criar_usuario(
        nome="Cliente Pedido",
        email="cliente@teste.com",
        perfil="cliente"
    )

    autenticar(administrador)

    _, variante, estoque = criar_produto_com_estoque(
        quantidade=10,
        preco="150.00"
    )

    resposta = client.post(
        "/pedido/criar",
        json={
            "cliente_id": cliente.id,
            "itens": [
                {
                    "variante_id": variante.id,
                    "quantidade": 2
                }
            ]
        }
    )

    dados = resposta.get_json()

    db.session.refresh(estoque)

    pedido = Pedido.query.first()

    assert resposta.status_code == 200
    assert dados["status"] == "ok"
    assert dados["total"] == 300.0
    assert estoque.quantidade == 8
    assert pedido.cliente_id == cliente.id
    assert pedido.status == "criado"
    assert len(pedido.itens) == 1


def test_cancelar_pedido_devolve_estoque(
    client,
    criar_usuario,
    autenticar
):
    administrador = criar_usuario(
        email="admin@teste.com",
        perfil="admin"
    )

    cliente = criar_usuario(
        nome="Cliente Pedido",
        email="cliente@teste.com",
        perfil="cliente"
    )

    autenticar(administrador)

    _, variante, estoque = criar_produto_com_estoque(
        quantidade=10
    )

    venda = client.post(
        "/pedido/criar",
        json={
            "cliente_id": cliente.id,
            "itens": [
                {
                    "variante_id": variante.id,
                    "quantidade": 2
                }
            ]
        }
    )

    pedido_id = venda.get_json()["pedido_id"]

    cancelamento = client.patch(
        f"/pedido/{pedido_id}/cancelar"
    )

    dados = cancelamento.get_json()

    db.session.refresh(estoque)

    pedido = db.session.get(Pedido, pedido_id)

    assert cancelamento.status_code == 200
    assert dados["status"] == "ok"
    assert pedido.status == "cancelado"
    assert estoque.quantidade == 10

    segundo_cancelamento = client.patch(
        f"/pedido/{pedido_id}/cancelar"
    )

    assert segundo_cancelamento.status_code == 400

    db.session.refresh(estoque)

    assert estoque.quantidade == 10