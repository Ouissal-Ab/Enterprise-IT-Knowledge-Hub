from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, categories, chat, documents, search, users
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"message": "API is running"}