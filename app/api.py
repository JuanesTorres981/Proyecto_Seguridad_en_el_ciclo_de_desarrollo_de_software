from fastapi import FastAPI

app = FastAPI()

fake_transactions = [
    {
        "user": "Juan",
        "amount": 5000,
        "risk": "high"
    },
    {
        "user": "Ana",
        "amount": 200,
        "risk": "low"
    }
]

@app.get("/")
def home():
    return {"message": "API funcionando"}

@app.get("/transactions")
def get_transactions():
    return fake_transactions