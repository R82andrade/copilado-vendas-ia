from fastapi import FastAPI

from app.routers.cliente import router as cliente_router
from app.routers.conversa import router as conversa_router
from app.routers.pedido import router as pedido_router
from app.routers.produto import router as produto_router

app = FastAPI(
    title="vendas-api",
    description="API para apoio inteligente ao atendimento e vendas.",
    version="0.1.0"
)

app.include_router(cliente_router)
app.include_router(produto_router)
app.include_router(pedido_router)
app.include_router(conversa_router)
