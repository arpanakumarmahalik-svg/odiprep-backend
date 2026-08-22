from fastapi import FastAPI
from routers import upload, test, results, lockout

app = FastAPI(
    title="OdiPrep Backend",
    description="AI-powered exam preparation for Odisha polytechnic students",
    version="1.0.0"
)

# Connect all routers
app.include_router(upload.router)
app.include_router(test.router)
app.include_router(results.router)
app.include_router(lockout.router)

@app.get("/")
def read_root():
    return {"message": "OdiPrep backend is running!"}