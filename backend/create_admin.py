from getpass import getpass

from werkzeug.security import generate_password_hash

from app import app
from database import db
from models import Usuario


def solicitar_dados():
    print()
    print("=== Criação do administrador ===")
    print()

    nome = input("Nome: ").strip()
    email = input("E-mail: ").strip().lower()

    if len(nome) < 3:
        raise ValueError(
            "O nome precisa ter pelo menos 3 caracteres."
        )

    if "@" not in email or "." not in email:
        raise ValueError("Informe um e-mail válido.")

    senha = getpass("Senha (mínimo de 8 caracteres): ")
    confirmar_senha = getpass("Confirme a senha: ")

    if len(senha) < 8:
        raise ValueError(
            "A senha precisa ter pelo menos 8 caracteres."
        )

    if senha != confirmar_senha:
        raise ValueError("As senhas não coincidem.")

    return nome, email, senha


def criar_administrador():
    try:
        nome, email, senha = solicitar_dados()

        with app.app_context():
            db.create_all()

            usuario_existente = Usuario.query.filter_by(
                email=email
            ).first()

            if usuario_existente:
                print()
                print(
                    "Não foi possível criar a conta: "
                    "esse e-mail já está cadastrado."
                )
                return

            administrador = Usuario(
                nome=nome,
                email=email,
                senha_hash=generate_password_hash(senha),
                perfil="admin",
                ativo=True
            )

            db.session.add(administrador)
            db.session.commit()

            print()
            print("Administrador criado com sucesso!")

    except ValueError as erro:
        print()
        print(f"Erro: {erro}")

    except Exception as erro:
        db.session.rollback()

        print()
        print(
            "Não foi possível criar o administrador: "
            f"{erro}"
        )


if __name__ == "__main__":
    criar_administrador()