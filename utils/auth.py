"""
Auth helpers — MySQL (utils/db.py) ke through kaam karte hain.
users.json ko ab sirf migration ke liye use kiya jata hai (utils/db.py mein).
"""
from utils.db import db_verify_login, db_create_user


def verify_login(username: str, password: str) -> bool:
    return db_verify_login(username, password)


def create_user(
    username: str,
    password: str,
    confirm: str,
    full_name: str = "",
    email: str = "",
) -> tuple:
    return db_create_user(username, password, confirm, full_name, email)
