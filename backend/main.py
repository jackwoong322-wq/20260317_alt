"""FastAPI 백엔드 — 차트 데이터 API"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import coins, chart, predictions

app = FastAPI(title="CryptoChart API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(coins.router,       prefix="/api")
app.include_router(chart.router,       prefix="/api")
app.include_router(predictions.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
