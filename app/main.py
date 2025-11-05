from fastapi import FastAPI
from app.api.routes import router as api_router


app = FastAPI(title="Corporate Integration App")

app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "App is running!"}
