"""Promote an existing account to superuser.

    poetry run python -m app.scripts.make_superuser someone@ispras.ru
    poetry run python -m app.scripts.make_superuser someone@ispras.ru --revoke
"""

import argparse
import asyncio
import sys

from app.core.logging_config import setup_logging
from app.core.unit_of_work import UnitOfWork
from app.db.database import AsyncSessionLocal
from app.users.exceptions import UserNotFoundError
from app.users.services import UserService


async def _set_superuser(email: str, is_superuser: bool) -> None:
    async with AsyncSessionLocal() as session:
        user = await UserService(UnitOfWork(session)).set_superuser(email, is_superuser)
    state = "superuser" if user.is_superuser else "regular user"
    print(f"{user.email} is now a {state}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="email of an existing account")
    parser.add_argument(
        "--revoke", action="store_true", help="take the superuser flag away instead"
    )
    args = parser.parse_args()
    setup_logging()
    try:
        asyncio.run(_set_superuser(args.email, not args.revoke))
    except UserNotFoundError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
