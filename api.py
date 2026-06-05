# api.py
import os

from fastapi import Body, FastAPI, Header, HTTPException

from main import FAST_PATH
from wrapper import FastWrapper


app = FastAPI(title="FAST Python Wrapper")


def verify_api_key(x_api_key):
    expected_key = os.environ.get("FAST_API_KEY")

    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )


def get_wrapper():
    wrapper = getattr(app.state, "fast_wrapper", None)

    if not wrapper:
        wrapper = FastWrapper(FAST_PATH)
        wrapper.start()
        app.state.fast_wrapper = wrapper

    return wrapper


@app.on_event("shutdown")
def shutdown():
    wrapper = getattr(app.state, "fast_wrapper", None)

    if wrapper:
        wrapper.stop()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run_fast(inputs=Body(default_factory=dict), x_api_key=Header(None)):
    verify_api_key(x_api_key)

    try:
        wrapper = get_wrapper()
        return wrapper.run(
            spec_name=inputs.get("spec_name"),
            mission_name=inputs.get("mission_name"),
            aircraft=inputs.get("aircraft"),
            mission=inputs.get("mission"),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
