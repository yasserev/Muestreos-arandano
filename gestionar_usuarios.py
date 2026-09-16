"""
Script para administrar usuarios del Dashboard de Control de Pesos (Camposol).
Permite crear, listar, modificar contraseñas y desactivar usuarios en data_pesos.db.
"""

import sys
import argparse
import sqlite3

# Ensure safe printing on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from data_engine import DB_PATH, init_users_table, create_or_update_user

def listar_usuarios():
    init_users_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, usuario, nombre, rol, activo, creado_el FROM usuarios ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    print("\n" + "=" * 75)
    print(f"{'ID':<4} | {'USUARIO':<15} | {'NOMBRE':<25} | {'ROL':<10} | {'ACTIVO':<6}")
    print("=" * 75)
    for r in rows:
        activo_str = "Si" if r["activo"] else "No"
        print(f"{r['id']:<4} | {r['usuario']:<15} | {str(r['nombre']):<25} | {str(r['rol']):<10} | {activo_str:<6}")
    print("=" * 75 + "\n")

def crear_o_modificar(usuario, password, nombre, rol='analista', activo=1):
    create_or_update_user(usuario, password, nombre, rol, activo)
    print(f"\n[OK] Usuario '{usuario}' guardado exitosamente con rol '{rol}'.")

def cambiar_estado(usuario, activo):
    init_users_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE usuarios SET activo = ? WHERE LOWER(usuario) = LOWER(?)", (activo, usuario.strip()))
    if cur.rowcount > 0:
        conn.commit()
        estado = "activado" if activo else "desactivado"
        print(f"\n[OK] Usuario '{usuario}' {estado} exitosamente.")
    else:
        print(f"\n[AVISO] No se encontro al usuario '{usuario}'.")
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Administración de Usuarios del Dashboard")
    parser.add_argument('--listar', action='store_true', help="Listar todos los usuarios")
    parser.add_argument('--crear', nargs=3, metavar=('USUARIO', 'PASSWORD', 'NOMBRE'), help="Crear o actualizar usuario: --crear <user> <pass> <nombre>")
    parser.add_argument('--rol', default='analista', help="Rol del usuario (default: analista)")
    parser.add_argument('--desactivar', metavar='USUARIO', help="Desactivar usuario")
    parser.add_argument('--activar', metavar='USUARIO', help="Activar usuario")

    args = parser.parse_args()

    if args.listar:
        listar_usuarios()
    elif args.crear:
        crear_o_modificar(args.crear[0], args.crear[1], args.crear[2], rol=args.rol)
        listar_usuarios()
    elif args.desactivar:
        cambiar_estado(args.desactivar, 0)
        listar_usuarios()
    elif args.activar:
        cambiar_estado(args.activar, 1)
        listar_usuarios()
    else:
        # Modo interactivo si no se pasan argumentos
        listar_usuarios()
        print("Uso rápido:")
        print("  python gestionar_usuarios.py --listar")
        print("  python gestionar_usuarios.py --crear <usuario> <password> \"<nombre>\"")
        print("  python gestionar_usuarios.py --desactivar <usuario>")
