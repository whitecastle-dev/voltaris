from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import re
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, validator
from typing import List, Optional
from passlib.context import CryptContext
from contextlib import asynccontextmanager
from bson import ObjectId

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de entorno
mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "voltaris_db")
cors_origins = os.getenv("CORS_ORIGINS", "https://voltarisindustry.com,http://localhost:3000").split(",")

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asegurar admin
    admin_user = await db.users.find_one({"username": "adminVoltaris"})
    if not admin_user:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": "adminVoltaris",
            "password": pwd_context.hash("Voltarisadmon2026*"),
            "role": "superadmin",
            "permissions": {"can_create": True, "can_edit": True, "can_delete": True}
        })
    yield

app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Ajusta según tu dominio real
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Project(BaseModel):
    title: str
    company_name: str
    category: str
    description: str
    date: Optional[str] = ""
    images: List[str] = []
    media_url: Optional[str] = ""

@api_router.get("/projects")
async def get_projects():
    projects = await db.projects.find({}).to_list(1000)
    return [{"id": str(p["_id"]), **{k:v for k,v in p.items() if k != "_id"}} for p in projects]

@api_router.post("/projects")
async def create_project(project: Project):
    result = await db.projects.insert_one(project.model_dump())
    return {"id": str(result.inserted_id)}

@api_router.put("/projects/{project_id}")
async def update_project(project_id: str, project: Project):
    await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": project.model_dump()})
    return {"message": "Actualizado"}

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    await db.projects.delete_one({"_id": ObjectId(project_id)})
    return {"message": "Eliminado"}

app.include_router(api_router)