from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cliente import Cliente
from app.models.conversa import Conversa
from app.models.mensagem import Mensagem
from app.models.produto import Produto


router = APIRouter(prefix="", tags=["Demo"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health():
    return {"status": "ok", "service": "vendas-api"}


@router.post("/demo/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.cpf == "12345678909").first()
    if not cliente:
        cliente = Cliente(
            nome="Maria Souza",
            cpf="12345678909",
            telefone="21998877666",
            email="maria@email.com",
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    produto = db.query(Produto).filter(Produto.nome == "Headset Pro").first()
    if not produto:
        produto = Produto(
            nome="Headset Pro",
            marca="AudioMax",
            categoria="Eletrônicos",
            preco=499.90,
            estoque=8,
            desconto_maximo=20,
        )
        db.add(produto)
        db.commit()
        db.refresh(produto)

    conversa = db.query(Conversa).filter(Conversa.cliente_id == cliente.id).first()
    if not conversa:
        conversa = Conversa(
            cliente_id=cliente.id,
            assunto="Dúvida sobre compra",
            status="em_atendimento",
            canal="chat",
        )
        db.add(conversa)
        db.commit()
        db.refresh(conversa)

    mensagem = db.query(Mensagem).filter(Mensagem.conversa_id == conversa.id).first()
    if not mensagem:
        mensagem = Mensagem(
            conversa_id=conversa.id,
            remetente="cliente",
            texto="Olá, ainda não recebi a confirmação do pedido.",
        )
        db.add(mensagem)
        db.commit()
        db.refresh(mensagem)

    return {
        "clientes": db.query(Cliente).count(),
        "produtos": db.query(Produto).count(),
        "conversas": db.query(Conversa).count(),
        "mensagens": db.query(Mensagem).count(),
    }
