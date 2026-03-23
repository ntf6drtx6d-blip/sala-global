from core.db import init_db, create_user
from core.auth import hash_password

# 1. створюємо базу (якщо ще нема)
init_db()

# 2. створюємо користувача
create_user(
    email="admin@sala.com",
    password_hash=hash_password("1234"),
    role="admin",
    full_name="Admin",
    organization="SALA"
)

print("Admin user created.")
