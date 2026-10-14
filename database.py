"""database.py - SQLite3 con consultas parametrizadas (anti Inyección SQL)."""
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import date, datetime

from models import Destino, PaqueteTuristico, Reserva, Usuario
from security import hash_password

ADMIN_EMAIL = "admin@viajesaventura.com"
# La contraseña inicial NO está en el código: se toma de la variable de entorno
# VIAJES_ADMIN_PASS o, si no existe, se genera una aleatoria que se muestra una sola vez.
ENV_ADMIN_PASS = "VIAJES_ADMIN_PASS"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('admin', 'cliente'))
);
CREATE TABLE IF NOT EXISTS destinos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    pais TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    costo REAL NOT NULL CHECK (costo >= 0),
    dias INTEGER NOT NULL CHECK (dias > 0)
);
CREATE TABLE IF NOT EXISTS paquetes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    descuento REAL NOT NULL DEFAULT 0 CHECK (descuento BETWEEN 0 AND 100),
    cupos INTEGER NOT NULL DEFAULT 20 CHECK (cupos > 0)
);
CREATE TABLE IF NOT EXISTS paquete_destinos (
    paquete_id INTEGER NOT NULL REFERENCES paquetes(id) ON DELETE CASCADE,
    destino_id INTEGER NOT NULL REFERENCES destinos(id) ON DELETE RESTRICT,
    orden INTEGER NOT NULL,
    PRIMARY KEY (paquete_id, destino_id)
);
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    paquete_id INTEGER NOT NULL REFERENCES paquetes(id) ON DELETE RESTRICT,
    personas INTEGER NOT NULL CHECK (personas > 0),
    total REAL NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Confirmada',
    fecha_reserva TEXT NOT NULL
);
"""


class Database:
    """Acceso a datos compartido por la consola y la GUI."""

    def __init__(self, ruta: str = "viajes_aventura.db"):
        self.ruta = ruta
        with closing(self._conn()) as con, con:
            con.executescript(ESQUEMA)
            columnas = [c["name"] for c in con.execute("PRAGMA table_info(paquetes)")]
            if "cupos" not in columnas:  # migración de BD creadas con la versión anterior
                con.execute("ALTER TABLE paquetes ADD COLUMN cupos INTEGER NOT NULL DEFAULT 20")
        self._crear_admin_inicial()

    # ------------------------- utilidades internas -------------------------
    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.ruta)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with closing(self._conn()) as con, con:
            cur = con.execute(sql, params)
            return cur

    def _query(self, sql: str, params: tuple = ()) -> list:
        with closing(self._conn()) as con:
            return con.execute(sql, params).fetchall()

    def _crear_admin_inicial(self) -> None:
        if self._query("SELECT 1 FROM usuarios WHERE rol = 'admin' LIMIT 1"):
            return
        clave = os.environ.get(ENV_ADMIN_PASS)
        generada = clave is None
        if generada:
            clave = secrets.token_urlsafe(12)
        self.crear_usuario("Administrador", ADMIN_EMAIL, hash_password(clave), "admin")
        if generada:
            print("=" * 60)
            print(" Cuenta administradora creada (esto se muestra UNA sola vez)")
            print(f"   Correo:     {ADMIN_EMAIL}")
            print(f"   Contraseña: {clave}")
            print(" Cámbiela desde el menú tras iniciar sesión.")
            print("=" * 60)

    # ------------------------------ Usuarios ------------------------------
    def crear_usuario(self, nombre, email, password_hash, rol="cliente") -> int:
        try:
            return self._exec(
                "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
                (nombre, email, password_hash, rol)).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Ya existe un usuario con ese correo.") from None

    def obtener_credenciales(self, email: str):
        filas = self._query("SELECT * FROM usuarios WHERE email = ?", (email,))
        if not filas:
            return None
        f = filas[0]
        return Usuario(f["id"], f["nombre"], f["email"], f["rol"]), f["password_hash"]

    def actualizar_password(self, usuario_id: int, password_hash: str) -> None:
        self._exec("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                   (password_hash, usuario_id))

    def listar_usuarios(self) -> list:
        return [Usuario(f["id"], f["nombre"], f["email"], f["rol"])
                for f in self._query("SELECT id, nombre, email, rol FROM usuarios ORDER BY id")]

    # ------------------------------ Destinos ------------------------------
    @staticmethod
    def _a_destino(f) -> Destino:
        return Destino(f["id"], f["nombre"], f["pais"], f["descripcion"], f["costo"], f["dias"])

    def crear_destino(self, nombre, pais, descripcion, costo, dias) -> int:
        return self._exec(
            "INSERT INTO destinos (nombre, pais, descripcion, costo, dias) VALUES (?, ?, ?, ?, ?)",
            (nombre, pais, descripcion, costo, dias)).lastrowid

    def listar_destinos(self) -> list:
        return [self._a_destino(f) for f in self._query("SELECT * FROM destinos ORDER BY nombre")]

    def obtener_destino(self, destino_id: int):
        filas = self._query("SELECT * FROM destinos WHERE id = ?", (destino_id,))
        return self._a_destino(filas[0]) if filas else None

    def actualizar_destino(self, destino_id, nombre, pais, descripcion, costo, dias) -> None:
        cur = self._exec(
            "UPDATE destinos SET nombre=?, pais=?, descripcion=?, costo=?, dias=? WHERE id=?",
            (nombre, pais, descripcion, costo, dias, destino_id))
        if cur.rowcount == 0:
            raise ValueError("El destino no existe.")

    def eliminar_destino(self, destino_id: int) -> None:
        try:
            cur = self._exec("DELETE FROM destinos WHERE id = ?", (destino_id,))
        except sqlite3.IntegrityError:
            raise ValueError("El destino está incluido en paquetes; no se puede eliminar.") from None
        if cur.rowcount == 0:
            raise ValueError("El destino no existe.")

    # ------------------------------ Paquetes ------------------------------
    def crear_paquete(self, nombre, fecha_inicio, descuento, destino_ids, cupos=20) -> int:
        if not destino_ids:
            raise ValueError("Seleccione al menos un destino.")
        with closing(self._conn()) as con, con:  # una sola transacción
            pid = con.execute(
                "INSERT INTO paquetes (nombre, fecha_inicio, descuento, cupos) VALUES (?, ?, ?, ?)",
                (nombre, fecha_inicio, descuento, cupos)).lastrowid
            con.executemany(
                "INSERT INTO paquete_destinos (paquete_id, destino_id, orden) VALUES (?, ?, ?)",
                [(pid, did, i) for i, did in enumerate(destino_ids)])
        return pid

    def actualizar_paquete(self, paquete_id, nombre, fecha_inicio, descuento,
                           destino_ids, cupos) -> None:
        if not destino_ids:
            raise ValueError("Seleccione al menos un destino.")
        with closing(self._conn()) as con, con:
            if con.execute("SELECT 1 FROM paquetes WHERE id = ?", (paquete_id,)).fetchone() is None:
                raise ValueError("El paquete no existe.")
            ocupados = self._plazas_ocupadas(con, paquete_id)
            if cupos < ocupados:
                raise ValueError(f"Los cupos no pueden ser menores a las plazas ya reservadas ({ocupados}).")
            con.execute("UPDATE paquetes SET nombre=?, fecha_inicio=?, descuento=?, cupos=? WHERE id=?",
                        (nombre, fecha_inicio, descuento, cupos, paquete_id))
            con.execute("DELETE FROM paquete_destinos WHERE paquete_id = ?", (paquete_id,))
            con.executemany(
                "INSERT INTO paquete_destinos (paquete_id, destino_id, orden) VALUES (?, ?, ?)",
                [(paquete_id, did, i) for i, did in enumerate(destino_ids)])

    @staticmethod
    def _plazas_ocupadas(con, paquete_id: int) -> int:
        return con.execute(
            "SELECT COALESCE(SUM(personas), 0) FROM reservas "
            "WHERE paquete_id = ? AND estado = 'Confirmada'", (paquete_id,)).fetchone()[0]

    def _armar_paquete(self, con, f) -> PaqueteTuristico:
        destinos = con.execute(
            "SELECT d.* FROM destinos d JOIN paquete_destinos pd ON pd.destino_id = d.id "
            "WHERE pd.paquete_id = ? ORDER BY pd.orden", (f["id"],)).fetchall()
        return PaqueteTuristico(
            f["id"], f["nombre"], f["fecha_inicio"], f["descuento"],
            [self._a_destino(d) for d in destinos],
            cupos=f["cupos"], reservados=self._plazas_ocupadas(con, f["id"]))

    def listar_paquetes(self) -> list:
        with closing(self._conn()) as con:
            filas = con.execute("SELECT * FROM paquetes ORDER BY fecha_inicio").fetchall()
            return [self._armar_paquete(con, f) for f in filas]

    def obtener_paquete(self, paquete_id: int):
        with closing(self._conn()) as con:
            f = con.execute("SELECT * FROM paquetes WHERE id = ?", (paquete_id,)).fetchone()
            return self._armar_paquete(con, f) if f else None

    def eliminar_paquete(self, paquete_id: int) -> None:
        try:
            cur = self._exec("DELETE FROM paquetes WHERE id = ?", (paquete_id,))
        except sqlite3.IntegrityError:
            raise ValueError("El paquete tiene reservas; no se puede eliminar.") from None
        if cur.rowcount == 0:
            raise ValueError("El paquete no existe.")

    # ------------------------------ Reservas ------------------------------
    def crear_reserva(self, usuario_id, paquete_id, personas) -> int:
        if not isinstance(personas, int) or personas < 1:
            raise ValueError("El número de personas debe ser al menos 1.")
        with closing(self._conn()) as con, con:
            con.execute("BEGIN IMMEDIATE")  # evita sobreventa si hay reservas simultáneas
            f = con.execute("SELECT * FROM paquetes WHERE id = ?", (paquete_id,)).fetchone()
            if f is None:
                raise ValueError("El paquete no existe.")
            paquete = self._armar_paquete(con, f)
            if date.fromisoformat(paquete.fecha_inicio) < date.today():
                raise ValueError("El paquete ya inició; no admite reservas.")
            if personas > paquete.disponibles:
                raise ValueError(f"Cupos insuficientes: quedan {paquete.disponibles}.")
            total = round(paquete.costo_total * personas, 2)
            return con.execute(
                "INSERT INTO reservas (usuario_id, paquete_id, personas, total, estado, fecha_reserva) "
                "VALUES (?, ?, ?, ?, 'Confirmada', ?)",
                (usuario_id, paquete_id, personas, total,
                 datetime.now().strftime("%Y-%m-%d %H:%M"))).lastrowid

    def listar_reservas(self, usuario_id=None) -> list:
        sql = ("SELECT r.*, u.nombre AS unombre, p.nombre AS pnombre FROM reservas r "
               "JOIN usuarios u ON u.id = r.usuario_id JOIN paquetes p ON p.id = r.paquete_id")
        params: tuple = ()
        if usuario_id is not None:
            sql += " WHERE r.usuario_id = ?"
            params = (usuario_id,)
        sql += " ORDER BY r.id DESC"
        return [Reserva(f["id"], f["usuario_id"], f["paquete_id"], f["personas"], f["total"],
                        f["estado"], f["fecha_reserva"], f["unombre"], f["pnombre"])
                for f in self._query(sql, params)]

    def cancelar_reserva(self, reserva_id: int, usuario_id=None) -> None:
        sql = "UPDATE reservas SET estado='Cancelada' WHERE id=? AND estado='Confirmada'"
        params: tuple = (reserva_id,)
        if usuario_id is not None:  # un cliente solo cancela las suyas
            sql += " AND usuario_id = ?"
            params += (usuario_id,)
        if self._exec(sql, params).rowcount == 0:
            raise ValueError("Reserva no encontrada o ya cancelada.")
