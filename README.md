# Doctime Backend

Backend service for the Doctime project, built with FastAPI.

## Requirements

- Python 3.10+
- pip
- A virtual environment such as .venv

## Installation

Create and activate a virtual environment:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

Install project dependencies:

    .\.venv\Scripts\python.exe -m pip install -r requirements.txt

## Running the Project

Start the FastAPI development server with Uvicorn:

    .\.venv\Scripts\python.exe -m uvicorn main:app --reload

## Running Tests

Run the test suite with:

    .\.venv\Scripts\python.exe -m pytest -q

## Verified Dependency Notes

- fastapi
- starlette
- httpx
- pytest
- passlib
- bcrypt==4.0.1
- jdatetime
