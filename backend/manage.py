"""Local-only owner provisioning; no public signup or default passwords."""

import argparse
import getpass

from sqlalchemy import delete

from backend.auth import hasher
from backend.config import Settings
from backend.db import connect, initialize
from backend.models import LoginSession, User


def main() -> None:
    parser = argparse.ArgumentParser(description="Administración local de PhotoHearth")
    parser.add_argument("command", choices=["create-user", "reset-password"])
    parser.add_argument("--name", default="Mi hogar")
    args = parser.parse_args()
    if not 1 <= len(args.name.strip()) <= 80:
        parser.error("El nombre debe tener entre 1 y 80 caracteres.")
    settings = Settings()
    initialize(settings)
    with connect(settings) as db:
        exists = db.get(User, 1)
    if args.command == "create-user" and exists:
        parser.error("Ya existe una cuenta. Usa reset-password para cambiar su contraseña.")
    if args.command == "reset-password" and not exists:
        parser.error("Primero crea una cuenta con create-user.")
    password = getpass.getpass("Contraseña (12–128 caracteres): ")
    if not 12 <= len(password) <= 128:
        parser.error("La contraseña debe tener entre 12 y 128 caracteres.")
    if password != getpass.getpass("Repite la contraseña: "):
        parser.error("Las contraseñas no coinciden.")
    encoded = hasher.hash(password)
    with connect(settings) as db:
        if args.command == "create-user":
            db.add(User(id=1, name=args.name.strip(), password_hash=encoded))
        else:
            db.get(User, 1).password_hash = encoded
        db.execute(delete(LoginSession))
    print("Cuenta actualizada. Las sesiones anteriores se han cerrado.")


if __name__ == "__main__":
    main()
