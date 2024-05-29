from fastapi import FastAPI
import uvicorn
from routes import router
from game_logic import start_game_threads

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    start_game_threads()
    uvicorn.run(app, host="0.0.0.0", port=8000)