from fastapi import FastAPI
from routers import upload, test, results, proctoring
import os

app = FastAPI(
    title="OdiPrep Backend",
    description="AI-powered exam preparation for Odisha polytechnic students",
    version="1.0.0"
)

# Create required folders on startup
os.makedirs("uploads", exist_ok=True)
os.makedirs("tests", exist_ok=True)
os.makedirs("answer_sheets", exist_ok=True)

# Connect all routers
app.include_router(upload.router)
app.include_router(test.router)
app.include_router(results.router)
app.include_router(proctoring.router)

@app.get("/")
def read_root():
    return {"message": "OdiPrep backend is running!"}