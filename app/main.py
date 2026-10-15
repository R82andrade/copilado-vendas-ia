import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.auth import router as auth_router
from app.routers.cliente import router as cliente_router
from app.routers.conversa import router as conversa_router
from app.routers.demo import router as demo_router
from app.routers.ia import router as ia_router
from app.routers.pedido import router as pedido_router
from app.routers.produto import router as produto_router
from app.routers.financeiro import router as financeiro_router
from app.routers.whatsapp import router as whatsapp_router

app = FastAPI(
    title="vendas-api",
    description="API para apoio inteligente ao atendimento e vendas.",
    version="0.1.0"
)

origins = [origin.strip() for origin in os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(cliente_router)
app.include_router(produto_router)
app.include_router(financeiro_router)
app.include_router(pedido_router)
app.include_router(conversa_router)
app.include_router(demo_router)
app.include_router(ia_router)
app.include_router(whatsapp_router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_build_dir = frontend_dir / "dist"
if frontend_build_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_build_dir / "assets"), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(frontend_build_dir / "index.html")

    @app.get("/{frontend_path:path}", include_in_schema=False)
    def frontend_route(frontend_path: str):
        return FileResponse(frontend_build_dir / "index.html")
