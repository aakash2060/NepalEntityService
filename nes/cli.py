def main():
    """Entry point for api command."""
    import uvicorn
    uvicorn.run("nes.api.app:app", host="localhost", port=8000, reload=True)

def dev():
    import subprocess
    subprocess.run(["fastapi", "run", "--host", "localhost", "--port", "8000", "nes/api/app.py", "--reload"])

if __name__ == "__main__":
    main()