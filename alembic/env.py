from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import importlib.util
import pathlib

from core.database import Base

_proj = pathlib.Path(__file__).resolve().parent.parent
_model_files = {
    "zenith_admin_bot.models": _proj / "src" / "zenith_admin_bot" / "models.py",
    "zenith_ai_bot.models": _proj / "src" / "zenith_ai_bot" / "models.py",
    "zenith_crypto_bot.models": _proj / "src" / "zenith_crypto_bot" / "models.py",
    "zenith_group_bot.models": _proj / "src" / "zenith_group_bot" / "models.py",
    "zenith_support_bot.models": _proj / "src" / "zenith_support_bot" / "models.py",
}
for _name, _mp in _model_files.items():
    _spec = importlib.util.spec_from_file_location(_name, str(_mp))
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if url.startswith("${{") or url.startswith("driver://"):
        url = "postgresql+asyncpg://localhost/zenith"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")
    if not url or url.startswith("${{") or url.startswith("driver://"):
        print("No real DATABASE_URL configured. Use offline mode or set sqlalchemy.url in alembic.ini.")
        return

    sync_url = url.replace("+asyncpg", "").replace("+psycopg", "").split("?")[0]
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
