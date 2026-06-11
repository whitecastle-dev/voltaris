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

# --- MANTENEMOS TU CONFIGURACIÓN ORIGINAL ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "voltaris_db")
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# --- FUNCIONES DE SEGURIDAD ORIGINALES ---
def check_role(user: dict, required_role: str):
    if user.get("role") != required_role:
        raise HTTPException(status_code=403, detail="No tienes permisos suficientes")

async def ensure_superadmin():
    admin_user = await db.users.find_one({"username": "adminVoltaris"})
    if not admin_user:
        hashed_pw = pwd_context.hash("Voltarisadmon2026*")
        superadmin_doc = {
            "id": str(uuid.uuid4()), "username": "adminVoltaris", "password": hashed_pw,
            "role": "superadmin", "permissions": {"can_create": True, "can_edit": True, "can_delete": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(superadmin_doc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_superadmin()
    yield

app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# --- MODELOS ---
class UserPermissions(BaseModel):
    can_create: bool = True; can_edit: bool = True; can_delete: bool = True

class UserCreateRequest(BaseModel):
    username: str; password: str; role: str = "editor"; permissions: UserPermissions
    @validator('password')
    def validate_password_complexity(cls, v):
        if len(v) < 8 or not re.search(r'[A-Z]', v) or not re.search(r'\d', v):
            raise ValueError("Mínimo 8 caracteres, mayúsculas y números.")
        return v

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str; username: str; role: str; permissions: dict

# --- CAMBIO AQUÍ: MODELO DE PROYECTO FLEXIBLE PARA EL 422 ---
class Project(BaseModel):
    title: str
    company_name: str
    category: str
    date: Optional[str] = None
    description: str
    media_url: Optional[str] = "" 

# --- RUTAS ---
@api_router.post("/auth/login", response_model=UserResponse)
async def login(credentials: dict):
    user = await db.users.find_one({"username": credentials.get("username")})
    if not user or not pwd_context.verify(credentials.get("password"), user.get("password", "")):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return UserResponse(**user)

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(): return await db.users.find({}, {"_id": 0}).to_list(1000)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 1: return {"message": "Usuario eliminado"}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

# --- RUTAS DE PROYECTOS CORREGIDAS ---
@api_router.get("/projects")
async def get_projects(): return await db.projects.find({}, {"_id": 0}).to_list(1000)

@api_router.post("/projects")
async def create_project(project: Project):
    project_dict = project.model_dump()
    project_dict['id'] = str(uuid.uuid4())
    await db.projects.insert_one(project_dict)
    return {"message": "Proyecto creado", "id": project_dict['id']}

# --- CAMBIO AQUÍ: BORRADO POR EL CAMPO 'id' (UUID) ---
@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    result = await db.projects.delete_one({"id": project_id})
    if result.deleted_count == 1: return {"message": "Proyecto eliminado"}
    raise HTTPException(status_code=404, detail="Proyecto no encontrado")

app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["*"], allow_headers=["*"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))