from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pymongo.errors import PyMongoError

from app.api.v1.chat import router as chat_router

app = FastAPI(title="Intellectual Ai")


@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(_request: Request, _exc: PyMongoError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable. Start MongoDB locally or set MONGO_URI in .env "
            "(e.g. mongodb://127.0.0.1:27017 or Atlas)."
        },
    )


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=307)


app.include_router(chat_router, prefix="/api/v1")

