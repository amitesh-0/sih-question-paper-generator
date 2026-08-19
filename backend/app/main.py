from fastapi import FastAPI
from app.api.generation import router as generation_router

app = FastAPI(title="Strict MILP Generator: 3-Factor Marks & Bloom Targets")

app.include_router(generation_router, prefix="/api", tags=["generation"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the SIH Question Paper Generator API"}
