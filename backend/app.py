from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_app, db
from models import (
    Usuario, Produto, Variante, Estoque, MovimentoEstoque,
    Pedido, ItemPedido,
    registrar_entrada_variante, registrar_saida_variante
)
import os
from dotenv import load_dotenv
import re
from datetime import datetime
from functools import wraps

# Diretórios
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "../frontend")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=TEMPLATE_DIR)
init_app(app)

# 🔴 NOVO: CHAVE SECRETA OBRIGATÓRIA PARA SESSÕES
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY não encontrada no arquivo .env")

# -------------------
# Páginas (com verificação de login no /inicio)
# -------------------
def page_login_required(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))

        return funcao(*args, **kwargs)

    return protegida

def page_roles_required(*perfis_permitidos):
    def decorator(funcao):
        @wraps(funcao)
        def protegida(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("index"))

            if session.get("user_perfil") not in perfis_permitidos:
                return "Acesso negado: você não possui permissão.", 403

            return funcao(*args, **kwargs)

        return protegida

    return decorator

def api_login_required(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(
                status="erro",
                mensagem="Autenticação necessária"
            ), 401

        return funcao(*args, **kwargs)

    return protegida

def api_roles_required(*perfis_permitidos):
    def decorator(funcao):
        @wraps(funcao)
        def protegida(*args, **kwargs):
            if "user_id" not in session:
                return jsonify(
                    status="erro",
                    mensagem="Autenticação necessária"
                ), 401

            if session.get("user_perfil") not in perfis_permitidos:
                return jsonify(
                    status="erro",
                    mensagem="Você não possui permissão para esta ação"
                ), 403

            return funcao(*args, **kwargs)

        return protegida

    return decorator

@app.route("/inicio")
@page_login_required
def inicio_page():    
    # Envia o nome do usuário logado para o template
    return render_template("inicio.html", nome_usuario=session.get('user_nome'))

@app.route("/")
def index():
    # Se já estiver logado, redireciona para o início
    if 'user_id' in session:
        return redirect(url_for('inicio_page'))
    return render_template("login.html")

@app.route("/register_page")
@page_login_required
@page_roles_required("admin")
def register_page():
    return render_template("criar_conta.html")

# Rotas que não mudam (mantidas por segurança)
@app.route("/produtos")
@page_login_required
def produtos_page():
    return render_template("produtos.html")

@app.route("/clientes")
@page_login_required
@page_roles_required("admin")
def clientes_page():
    return render_template("clientes.html")

@app.route("/lista_cliente")
@page_login_required
@page_roles_required("admin")
def lista_cliente_page():
    return render_template("lista_clientes.html")

@app.route("/estoque")
@page_login_required
@page_roles_required("admin")
def estoque_page():
    return render_template("estoque.html")

@app.route("/faturamento")
@page_login_required
@page_roles_required("admin")
def faturamento_page():
    return render_template("faturamento.html")

# -------------------
# Util: gerar SKU simples
# -------------------
def gerar_sku_from_fields(produto_linha: str, altura=None, largura=None, cor=None, moldura=None):
    base = re.sub(r'[^A-Za-z0-9]', '', produto_linha[:3]).upper()
    parts = [base]
    if altura:
        parts.append(str(altura).replace('.', '').replace(',', ''))
    if largura:
        parts.append(str(largura).replace('.', '').replace(',', ''))
    if cor:
        parts.append(re.sub(r'[^A-Za-z0-9]', '', cor)[:6].upper())
    if moldura:
        parts.append(re.sub(r'[^A-Za-z0-9]', '', moldura)[:4].upper())
    sku = "-".join(parts)
    return sku[:60]


# -------------------
# Rotas de autenticação / registro
# -------------------

@app.route("/register", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def register():
    data = request.get_json()
    nome = data.get("nome")
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify(status="erro", mensagem="Preencha todos os campos"), 400

    if Usuario.query.filter_by(email=email.lower()).first():
        return jsonify(status="erro", mensagem="E-mail já cadastrado"), 400

    try:
        user = Usuario(
            nome=nome.lower() if nome else None,
            perfil="cliente",
            email=email.lower(),
            senha_hash=generate_password_hash(senha)
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(status="ok", mensagem="Conta criada com sucesso!")
    except Exception as e:
        db.session.rollback()
        return jsonify(status="erro", mensagem=str(e))


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")

    if not email or not senha:
        return jsonify(status="erro", mensagem="Preencha todos os campos"), 400

    user = Usuario.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify(status="erro", mensagem="Conta não encontrada"), 401

    if not check_password_hash(user.senha_hash, senha):
        return jsonify(status="erro", mensagem="Senha incorreta"), 401

    # 🟢 NOVO: Salva dados na Sessão do Flask (Server-Side)
    session['user_id'] = user.id
    session['user_nome'] = user.nome
    session['user_email'] = user.email
    session['user_perfil'] = user.perfil

    # Não precisa retornar o nome no JSON, o Flask Session cuida do estado
    return jsonify(status="ok", mensagem="Login realizado com sucesso")


@app.route("/logout")
@page_login_required
def logout():
    # 🟢 NOVO: Limpa a sessão e redireciona para o login
    session.clear()
    return redirect(url_for('index'))


# -------------------
# Teste DB
# -------------------

# -------------------
# Endpoints CRUD, Estoque, Pedidos e Atividades (Mantidos)
# -------------------
@app.route("/produto/variantes", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def criar_produto_com_variantes():
    """
    Cria um novo produto e suas variantes.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "payload JSON required"}), 400

    linha = data.get("linha")
    formato = data.get("formato")
    descricao = data.get("descricao")
    imagem_url = data.get("imagem_url")
    variantes = data.get("variantes", [])

    if not linha or not formato:
        return jsonify({"error": "linha and formato required"}), 400

    produto = Produto(
        linha=linha,
        formato=formato,
        descricao=descricao,
        imagem_url=imagem_url
    )
    try:
        db.session.add(produto)
        db.session.flush()

        resposta_variantes = []
        for v in variantes:
            altura = v.get("altura_cm")
            largura = v.get("largura_cm")
            cor = v.get("cor")
            moldura = v.get("moldura")
            preco_base = v.get("preco_base", 0)
            estoque_inicial = int(v.get("estoque_inicial", 0))

            sku_base = gerar_sku_from_fields(linha, altura, largura, cor, moldura)
            sku = sku_base
            i = 1
            while Variante.query.filter_by(sku=sku).first():
                i += 1
                sku = f"{sku_base}-{i}"

            variante = Variante(
                produto_id=produto.id,
                altura_cm=altura,
                largura_cm=largura,
                cor=cor,
                led_direto=bool(v.get("led_direto", False)),
                led_indireto=bool(v.get("led_indireto", False)),
                moldura=moldura,
                sku=sku,
                preco_base=preco_base,
                ativo=True
            )
            db.session.add(variante)
            db.session.flush()

            estoque = Estoque(
                variante_id=variante.id,
                quantidade=estoque_inicial,
                minimo=int(v.get("minimo", 0))
            )
            db.session.add(estoque)

            resposta_variantes.append({
                "variante_id": variante.id,
                "sku": sku,
                "preco_base": str(preco_base),
                "estoque_inicial": estoque_inicial
            })

        db.session.commit()
        return jsonify({"produto_id": produto.id, "variantes": resposta_variantes}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/produto/catalogo", methods=["GET"])
@api_login_required
def listar_catalogo():
    """ Retorna todas as variantes ativas com dados do produto e estoque. """
    q = db.session.query(Produto, Variante, Estoque) \
        .join(Variante, Variante.produto_id == Produto.id) \
        .outerjoin(Estoque, Estoque.variante_id == Variante.id) \
        .filter(Produto.ativo == True, Variante.ativo == True) \
        .all()

    resultado = []
    for prod, var, est in q:
        resultado.append({
    "produto_id": prod.id,
    "nome_produto": f"{prod.linha} {prod.formato}",
    "linha": prod.linha,
    "formato": prod.formato,
    "variante_id": var.id,
    "sku": var.sku,
    "altura_cm": float(var.altura_cm) if var.altura_cm is not None else None,
    "largura_cm": float(var.largura_cm) if var.largura_cm is not None else None,
    "cor": var.cor,
    "moldura": var.moldura,
    "preco_base": str(var.preco_base),
    "estoque": int(est.quantidade) if est is not None else 0
})
    return jsonify(resultado)


@app.route("/estoque/variantes", methods=["GET"])
@api_login_required
@api_roles_required("admin")
def listar_variantes_estoque():
    variantes = Variante.query.filter_by(ativo=True).all()
    resp = []
    for v in variantes:
        est = v.estoque
        resp.append({
            "variante_id": v.id,
            "produto_id": v.produto_id,
            "nome_produto": v.produto.linha,
            "formato": v.produto.formato,
            "sku": v.sku,
            "altura_cm": float(v.altura_cm) if v.altura_cm is not None else None,
            "largura_cm": float(v.largura_cm) if v.largura_cm is not None else None,
            "cor": v.cor,
            "moldura": v.moldura,
            "preco_base": str(v.preco_base),
            "estoque": int(est.quantidade) if est else 0,
            "minimo": int(est.minimo) if est else 0
        })
    return jsonify(resp)

@app.route("/estoque/entrada_sku", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def entrada_sku():
    """Payload: {"variante_id": 1, "quantidade": 5, "motivo": "compra"}"""
    data = request.get_json()
    variante_id = data.get("variante_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = session["user_id"]
    motivo = data.get("motivo", "Entrada manual")

    if not variante_id or quantidade <= 0:
        return jsonify({"error": "variante_id and quantidade>0 required"}), 400

    try:
        novo = registrar_entrada_variante(variante_id=variante_id, quantidade=quantidade, usuario_id=usuario_id, motivo=motivo)
        return jsonify({"status": "ok", "estoque_atual": novo})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


@app.route("/estoque/saida_sku", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def saida_sku():
    """Payload: {"variante_id": 1, "quantidade": 2, "motivo": "venda"}"""
    data = request.get_json()
    variante_id = data.get("variante_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = session["user_id"]
    motivo = data.get("motivo", "Saída por pedido")

    if not variante_id or quantidade <= 0:
        return jsonify({"error": "variante_id and quantidade>0 required"}), 400

    try:
        novo = registrar_saida_variante(variante_id=variante_id, quantidade=quantidade, usuario_id=usuario_id, motivo=motivo)
        return jsonify({"status": "ok", "estoque_atual": novo})
    except ValueError as ve:
        return jsonify({"status": "erro", "mensagem": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route("/estoque/entrada", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def entrada_estoque_compat():
    """ Endpoint legado: tenta localizar variante pelo produto e incrementar estoque da primeira variante. """
    data = request.get_json()
    produto_id = data.get("produto_id")
    quantidade = int(data.get("quantidade", 0))
    usuario_id = session["user_id"]

    if not produto_id or quantidade <= 0:
        return jsonify({"status": "erro", "mensagem": "produto_id and quantidade>0 required"}), 400

    variante = Variante.query.filter_by(produto_id=produto_id, ativo=True).first()
    if not variante:
        return jsonify({"status": "erro", "mensagem": "Nenhuma variante encontrada para o produto"}), 404

    try:
        novo = registrar_entrada_variante(variante_id=variante.id, quantidade=quantidade, usuario_id=usuario_id, motivo="Entrada compatibilidade produto")
        return jsonify({"status": "ok", "estoque_atual": novo})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 400


@app.route('/api/clientes', methods=['GET'])
@api_login_required
@api_roles_required("admin")
def api_clientes():
    clientes = Usuario.query.all()
    return jsonify([
        {
            "id": c.id,
            "nome": c.nome,
            "email": c.email
        }
        for c in clientes
    ])


@app.route("/pedido/criar", methods=["POST"])
@api_login_required
@api_roles_required("admin")
def criar_pedido():
    data = request.get_json(silent=True) or {}

    cliente_nome = data.get("cliente_nome")

    if not cliente_nome and data.get("cliente_id"):
        cliente_nome = f"Cliente ID {data.get('cliente_id')}"

    itens = data.get("itens", [])

    if not cliente_nome:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    if not itens:
        return jsonify({"error": "Nenhum item no pedido"}), 400

    usuario_responsavel = session["user_id"]

    try:
        pedido = Pedido(
            cliente_nome=cliente_nome,
            cliente_contato=None,
            status="criado",
            total=0,
            criado_por=usuario_responsavel
        )

        db.session.add(pedido)
        db.session.flush()

        total_geral = 0

        for item in itens:
            variante_id = item.get("variante_id")
            quantidade = item.get("quantidade")

            try:
                quantidade = int(quantidade)
            except (TypeError, ValueError):
                db.session.rollback()
                return jsonify({"error": "Quantidade inválida"}), 400

            if not variante_id or quantidade <= 0:
                db.session.rollback()
                return jsonify({"error": "Dados do item inválidos"}), 400

            variante = Variante.query.filter_by(
                id=variante_id,
                ativo=True
            ).first()

            if not variante:
                db.session.rollback()
                return jsonify({
                    "error": "Produto ou variante não encontrada"
                }), 404

            preco_unit = variante.preco_base

            estoque_registro = Estoque.query.filter_by(
                variante_id=variante_id
            ).first()

            if not estoque_registro:
                db.session.rollback()
                return jsonify({
                    "error": f"Estoque não encontrado para o item {variante_id}"
                }), 400

            if estoque_registro.quantidade < quantidade:
                db.session.rollback()
                return jsonify({
                    "error": (
                        "Estoque insuficiente. "
                        f"Disponível: {estoque_registro.quantidade}"
                    )
                }), 400

            estoque_registro.quantidade -= quantidade

            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                variante_id=variante_id,
                quantidade=quantidade,
                preco_unit=preco_unit,
                valor_total=preco_unit * quantidade
            )

            db.session.add(item_pedido)
            total_geral += preco_unit * quantidade

        pedido.total = total_geral
        db.session.commit()

        return jsonify({
            "status": "ok",
            "pedido_id": pedido.id,
            "total": float(total_geral)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/pedido/listar', methods=['GET'])
@api_login_required
@api_roles_required("admin")
def listar_pedidos():
    """ Lista pedidos com itens e informações das variantes. """
    pedidos = Pedido.query.order_by(Pedido.created_at.desc()).limit(100).all()
    resultado = []

    for p in pedidos:
        itens_processados = []
        for item in p.itens:
            var = Variante.query.get(item.variante_id)
            itens_processados.append({
                "variante_id": item.variante_id,
                "sku": var.sku if var else None,
                "quantidade": int(item.quantidade),
                "preco_unit": float(item.preco_unit),
                "valor_total": float(item.valor_total)
            })

        resultado.append({
            "id": p.id,
            "cliente_nome": p.cliente_nome,
            "total": float(p.total or 0),
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None,
            "itens": itens_processados
        })

    return jsonify(resultado)

@app.route("/variante/excluir/<int:id>", methods=["DELETE"])
@api_login_required
@api_roles_required("admin")
def excluir_variante(id):
    try:
        variante = Variante.query.get(id)
        if not variante:
            return jsonify({"status": "erro", "mensagem": "Variante não encontrada"}), 404
        
        if variante.estoque:
            variante.estoque.quantidade = 0
            
        variante.ativo = False
        
        db.session.commit()
        
        return jsonify({"status": "ok", "mensagem": "Produto removido com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
        

@app.route("/api/atividades_recentes")
@api_login_required
@api_roles_required("admin")
def api_atividades_recentes():
    atividades = []

    # Vendas
    ultimos_pedidos = Pedido.query.order_by(Pedido.created_at.desc()).limit(50).all()
    for p in ultimos_pedidos:
        qtd_total = sum([i.quantidade for i in p.itens])
        nome_exemplo = "Produtos diversos"
        if p.itens:
            primeiro_item = p.itens[0]
            var = Variante.query.get(primeiro_item.variante_id)
            if var and var.produto:
                nome_exemplo = f"{var.produto.linha}"
            else:
                nome_exemplo = "(Produto Excluído)"

        atividades.append({
            "id": p.id,
            "tipo": "venda",
            "icone": "💰",
            "titulo": "Venda Realizada",
            "descricao": f"{nome_exemplo} (e mais itens...)",
            "detalhe": f"{qtd_total} un. vendidas",
            "data": p.created_at.isoformat()
        })

    # Produtos (Apenas ativos)
    ultimos_produtos = Variante.query.filter_by(ativo=True).order_by(Variante.created_at.desc()).limit(50).all()
    for v in ultimos_produtos:
        nome_prod = "Produto"
        prod = Produto.query.get(v.produto_id)
        if prod:
            nome_prod = f"{prod.linha} {prod.formato}"
        
        qtd_inicial = 0
        if v.estoque:
            qtd_inicial = v.estoque.quantidade

        atividades.append({
            "id": v.id,
            "tipo": "cadastro",
            "icone": "✨",
            "titulo": "Novo Produto",
            "descricao": f"{nome_prod} - {v.cor}",
            "detalhe": f"Estoque inicial: {qtd_inicial}",
            "data": v.created_at.isoformat()
        })

    atividades.sort(key=lambda x: x['data'], reverse=True)
    return jsonify(atividades[:50])


@app.route("/pedido/excluir/<int:id>", methods=["DELETE"])
@api_login_required
@api_roles_required("admin")
def excluir_pedido(id):
    try:
        pedido = Pedido.query.get(id)
        if not pedido:
            return jsonify({"status": "erro", "mensagem": "Pedido não encontrado"}), 404
        
        ItemPedido.query.filter_by(pedido_id=id).delete()
        
        db.session.delete(pedido)
        db.session.commit()
        
        return jsonify({"status": "ok", "mensagem": "Venda excluída do histórico!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# -------------------
# Run
# -------------------
if __name__ == "__main__":
    debug_ativo = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_ativo)