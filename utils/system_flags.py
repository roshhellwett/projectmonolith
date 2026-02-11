from database.db import SessionLocal
from database.models import SystemFlag


def get_flag(key: str):
    db = SessionLocal()
    flag = db.query(SystemFlag).filter_by(key=key).first()
    db.close()

    if flag:
        return flag.value
    return None


def set_flag(key: str, value: str):
    db = SessionLocal()

    flag = db.query(SystemFlag).filter_by(key=key).first()

    if not flag:
        flag = SystemFlag(key=key, value=value)
        db.add(flag)
    else:
        flag.value = value

    db.commit()
    db.close()
