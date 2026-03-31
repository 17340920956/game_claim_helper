
import uvicorn
import multiprocessing
from app.main import app
from app.core.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
