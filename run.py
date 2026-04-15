import sys
import os
import uvicorn

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("dev", "start"):
        print("Usage: uv run run.py [dev|start]")
        sys.exit(1)

    reload = sys.argv[1] == "dev"
    uvicorn.run("main:app", reload=reload, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
