from .main import app
import uvicorn


def start():
    uvicorn.run(app)