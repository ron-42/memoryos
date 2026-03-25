import asyncio
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.sqlite import initialize_database


async def main() -> None:
    await initialize_database()
    print("SQLite database initialized.")


if __name__ == "__main__":
    asyncio.run(main())
