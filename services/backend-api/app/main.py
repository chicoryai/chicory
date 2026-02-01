import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import api_router
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.utils.rabbitmq_client import initialize_rabbitmq_queues, close_rabbitmq_connection

# Define lifespan context manager for database and RabbitMQ connections
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to database and initialize RabbitMQ queues
    await connect_to_mongo()
    initialize_rabbitmq_queues()
    yield
    # Shutdown: close database and RabbitMQ connections
    await close_mongo_connection()
    close_rabbitmq_connection()

app = FastAPI(
    title="Project Management API",
    description="API for managing projects and data sources",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Project Management API is running"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
