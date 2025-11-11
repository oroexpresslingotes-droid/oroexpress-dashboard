import json
from datetime import datetime
from werkzeug.security import generate_password_hash

USERS_FILE = "usuarios.json"


def reset_password(username, new_password):
    """Actualiza la contraseña de un usuario existente."""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ No existe el archivo usuarios.json")
        return

    if username not in data:
        print(f"⚠️ El usuario '{username}' no existe.")
        return

    data[username]["password"] = generate_password_hash(new_password)
    data[username]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Contraseña actualizada exitosamente para '{username}'.")


def crear_usuario(username, password, email="", role="admin"):
    """Crea un nuevo usuario con contraseña cifrada."""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    if username in data:
        print(f"⚠️ El usuario '{username}' ya existe.")
        return

    data[username] = {
        "password": generate_password_hash(password),
        "role": role,
        "email": email,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Usuario '{username}' creado con éxito.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 4 and sys.argv[1] == "crear":
        _, _, user, pwd = sys.argv
        crear_usuario(user, pwd)
    elif len(sys.argv) == 3:
        _, user, pwd = sys.argv
        reset_password(user, pwd)
    else:
        print("""
Uso:
  🔹 Cambiar contraseña existente:
      python reset_password.py <usuario> <nueva_contraseña>

  🔹 Crear usuario nuevo:
      python reset_password.py crear <usuario> <contraseña>
""")
