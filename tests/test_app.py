"""
Testes de integração para o Mini CRM.

Rodar com: pytest tests/ -v
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app, db, Cliente, Agendamento  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_home_page_carrega(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Painel".encode() in resposta.data


def test_criar_cliente(client):
    resposta = client.post(
        "/clientes/novo",
        data={"nome": "Maria Silva", "email": "maria@exemplo.com", "telefone": "11999999999"},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    with app.app_context():
        cliente = Cliente.query.filter_by(nome="Maria Silva").first()
        assert cliente is not None
        assert cliente.email == "maria@exemplo.com"


def test_criar_cliente_sem_nome_falha(client):
    resposta = client.post("/clientes/novo", data={"nome": ""}, follow_redirects=True)
    assert resposta.status_code == 200

    with app.app_context():
        assert Cliente.query.count() == 0


def test_editar_cliente(client):
    with app.app_context():
        cliente = Cliente(nome="João")
        db.session.add(cliente)
        db.session.commit()
        cliente_id = cliente.id

    client.post(
        f"/clientes/{cliente_id}/editar",
        data={"nome": "João Pedro", "email": "", "telefone": "", "observacoes": ""},
        follow_redirects=True,
    )

    with app.app_context():
        cliente_atualizado = db.session.get(Cliente, cliente_id)
        assert cliente_atualizado.nome == "João Pedro"


def test_excluir_cliente(client):
    with app.app_context():
        cliente = Cliente(nome="Cliente Temporário")
        db.session.add(cliente)
        db.session.commit()
        cliente_id = cliente.id

    client.post(f"/clientes/{cliente_id}/excluir", follow_redirects=True)

    with app.app_context():
        assert db.session.get(Cliente, cliente_id) is None


def test_criar_agendamento(client):
    with app.app_context():
        cliente = Cliente(nome="Ana")
        db.session.add(cliente)
        db.session.commit()
        cliente_id = cliente.id

    amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    resposta = client.post(
        "/agendamentos/novo",
        data={"cliente_id": cliente_id, "titulo": "Reunião", "data_hora": amanha},
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    with app.app_context():
        agendamento = Agendamento.query.filter_by(titulo="Reunião").first()
        assert agendamento is not None
        assert agendamento.status == "agendado"


def test_atualizar_status_agendamento(client):
    with app.app_context():
        cliente = Cliente(nome="Carlos")
        db.session.add(cliente)
        db.session.commit()
        agendamento = Agendamento(
            cliente_id=cliente.id, titulo="Consulta", data_hora=datetime.now()
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    client.post(f"/agendamentos/{agendamento_id}/status/concluido", follow_redirects=True)

    with app.app_context():
        atualizado = db.session.get(Agendamento, agendamento_id)
        assert atualizado.status == "concluido"


def test_status_invalido_nao_atualiza(client):
    with app.app_context():
        cliente = Cliente(nome="Beatriz")
        db.session.add(cliente)
        db.session.commit()
        agendamento = Agendamento(
            cliente_id=cliente.id, titulo="Follow-up", data_hora=datetime.now()
        )
        db.session.add(agendamento)
        db.session.commit()
        agendamento_id = agendamento.id

    client.post(f"/agendamentos/{agendamento_id}/status/invalido", follow_redirects=True)

    with app.app_context():
        atualizado = db.session.get(Agendamento, agendamento_id)
        assert atualizado.status == "agendado"
