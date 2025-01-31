from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import team, task, users

app = FastAPI(title="Gmail Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(team.router)
app.include_router(task.router)
app.include_router(users.router)

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI MVP!"} 