# api.py
import os

from fastapi import Body, FastAPI, Header, HTTPException

from main import FAST_PATH
from wrapper import FastWrapper


app = FastAPI(title="FAST Python Wrapper")


def verify_api_key(x_api_key):
    # Authentication is optional for local use. If FAST_API_KEY is unset, every
    # request is allowed; if it is set, callers must send the matching x-api-key.
    expected_key = os.environ.get("FAST_API_KEY")

    if expected_key and x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )


def get_wrapper():
    # Starting MATLAB is expensive, so the API keeps one FastWrapper instance on
    # app.state and reuses the same MATLAB Engine process across requests.
    wrapper = getattr(app.state, "fast_wrapper", None)

    if not wrapper:
        wrapper = FastWrapper(FAST_PATH)
        wrapper.start()
        app.state.fast_wrapper = wrapper

    return wrapper


@app.on_event("shutdown")
def shutdown():
    # Make sure uvicorn shutdown also stops MATLAB. Without this, a local dev
    # session can leave matlab.exe running in the background.
    wrapper = getattr(app.state, "fast_wrapper", None)

    if wrapper:
        wrapper.stop()


@app.get("/health")
def health():
    # Lightweight check that does not start MATLAB. Use /run to verify the full
    # FAST/MATLAB path.
    return {"status": "ok"}


@app.post("/run")
def run_fast(inputs=Body(default_factory=dict), x_api_key=Header(None)):
    verify_api_key(x_api_key)

    try:
        wrapper = get_wrapper()

        # The API supports both wrapper modes:
        # - spec_name + mission_name for built-in FAST package functions.
        # - aircraft + mission dictionaries for callers that send full structs.
        return wrapper.run(
            spec_name=inputs.get("spec_name"),
            mission_name=inputs.get("mission_name"),
            aircraft=inputs.get("aircraft"),
            mission=inputs.get("mission"),
        )
    except Exception as error:
        # Preserve the MATLAB/FAST error text in the HTTP response. This keeps
        # the local API useful for debugging model setup problems.
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
