"""
Mini CRM + Agendamento

Aplicação web simples em Flask para cadastrar clientes e agendar
compromissos com eles (ex: reuniões, atendimentos, consultas).

Autor: Júnior Rodrigues
"""

import os
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-troque-em-producao")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'crm.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(30), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    agendamentos = db.relationship(
        "Agendamento", backref="cliente", cascade="all, delete-orphan"
    )


class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="agendado")  # agendado, concluido, cancelado


@app.route("/")
def index():
    total_clientes = Cliente.query.count()
    proximos = (
        Agendamento.query.filter(Agendamento.status == "agendado")
        .order_by(Agendamento.data_hora.asc())
        .limit(5)
        .all()
    )
    return render_template("index.html", total_clientes=total_clientes, proximos=proximos)


# ----- Clientes (CRUD) -----

@app.route("/clientes")
def listar_clientes():
    termo = request.args.get("q", "").strip()
    query = Cliente.query
    if termo:
        query = query.filter(Cliente.nome.ilike(f"%{termo}%"))
    clientes = query.order_by(Cliente.nome.asc()).all()
    return render_template("clientes.html", clientes=clientes, termo=termo)


@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("O nome é obrigatório.", "error")
            return render_template("form_cliente.html", cliente=None)

        cliente = Cliente(
            nome=nome,
            email=request.form.get("email", "").strip(),
            telefone=request.form.get("telefone", "").strip(),
            observacoes=request.form.get("observacoes", "").strip(),
        )
        db.session.add(cliente)
        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("listar_clientes"))

    return render_template("form_cliente.html", cliente=None)


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    if request.method == "POST":
        cliente.nome = request.form.get("nome", "").strip()
        cliente.email = request.form.get("email", "").strip()
        cliente.telefone = request.form.get("telefone", "").strip()
        cliente.observacoes = request.form.get("observacoes", "").strip()
        db.session.commit()
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("listar_clientes"))

    return render_template("form_cliente.html", cliente=cliente)


@app.route("/clientes/<int:cliente_id>/excluir", methods=["POST"])
def excluir_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente removido.", "success")
    return redirect(url_for("listar_clientes"))


# ----- Agendamentos -----

@app.route("/agendamentos")
def listar_agendamentos():
    agendamentos = Agendamento.query.order_by(Agendamento.data_hora.asc()).all()
    return render_template("agendamentos.html", agendamentos=agendamentos)


@app.route("/agendamentos/novo", methods=["GET", "POST"])
def novo_agendamento():
    clientes = Cliente.query.order_by(Cliente.nome.asc()).all()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        titulo = request.form.get("titulo", "").strip()
        data_hora_str = request.form.get("data_hora", "")

        if not (cliente_id and titulo and data_hora_str):
            flash("Preencha todos os campos obrigatórios.", "error")
            return render_template("form_agendamento.html", clientes=clientes, agendamento=None)

        agendamento = Agendamento(
            cliente_id=int(cliente_id),
            titulo=titulo,
            data_hora=datetime.fromisoformat(data_hora_str),
        )
        db.session.add(agendamento)
        db.session.commit()
        flash("Agendamento criado com sucesso!", "success")
        return redirect(url_for("listar_agendamentos"))

    return render_template("form_agendamento.html", clientes=clientes, agendamento=None)


@app.route("/agendamentos/<int:agendamento_id>/status/<string:novo_status>", methods=["POST"])
def atualizar_status_agendamento(agendamento_id, novo_status):
    if novo_status not in {"agendado", "concluido", "cancelado"}:
        flash("Status inválido.", "error")
        return redirect(url_for("listar_agendamentos"))

    agendamento = Agendamento.query.get_or_404(agendamento_id)
    agendamento.status = novo_status
    db.session.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("listar_agendamentos"))


@app.route("/agendamentos/<int:agendamento_id>/excluir", methods=["POST"])
def excluir_agendamento(agendamento_id):
    agendamento = Agendamento.query.get_or_404(agendamento_id)
    db.session.delete(agendamento)
    db.session.commit()
    flash("Agendamento removido.", "success")
    return redirect(url_for("listar_agendamentos"))


def seed_dados_exemplo():
    if Cliente.query.count() > 0:
        return

    clientes = [
        Cliente(nome="Ana Beatriz Souza", email="ana.souza@example.com", telefone="(11) 98765-4321"),
        Cliente(nome="Carlos Eduardo Lima", email="carlos.lima@example.com", telefone="(21) 99888-7766"),
        Cliente(nome="Fernanda Costa", email="fernanda.costa@example.com", telefone="(31) 97777-1122"),
    ]
    db.session.add_all(clientes)
    db.session.commit()

    agendamentos = [
        Agendamento(cliente_id=clientes[0].id, titulo="Reunião de alinhamento", data_hora=datetime(2026, 8, 5, 14, 0)),
        Agendamento(cliente_id=clientes[1].id, titulo="Consulta inicial", data_hora=datetime(2026, 8, 7, 9, 30)),
        Agendamento(cliente_id=clientes[2].id, titulo="Follow-up de proposta", data_hora=datetime(2026, 8, 10, 16, 0)),
    ]
    db.session.add_all(agendamentos)
    db.session.commit()


def criar_banco():
    with app.app_context():
        db.create_all()
        seed_dados_exemplo()


criar_banco()

if __name__ == "__main__":
    app.run(debug=True)
