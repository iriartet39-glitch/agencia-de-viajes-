"""security.py - Hashing de contraseñas, autenticación y validación de entradas."""
import hashlib
import hmac
import math
import re
import secrets
import time
from datetime import date

ITERACIONES = 600_000  # recomendación OWASP para PBKDF2-HMAC-SHA256
MAX_INTENTOS = 5
BLOQUEO_SEG = 60

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# Letras (unicode), dígitos, espacios y puntuación básica; sin < > " ` ; etc.
TEXTO_RE = re.compile(r"^[\w\s.,:¡!¿?()\-'/#&%$+]+$", re.UNICODE)


class ValidationError(ValueError):
    """Error de validación de entrada del usuario."""


# ---------------------------- Contraseñas ----------------------------
def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 con salt aleatorio. Formato: pbkdf2$iter$salt$hash."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERACIONES)
    return f"pbkdf2${ITERACIONES}${salt.hex()}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    """Compara en tiempo constante contra el hash almacenado."""
    try:
        _, iters, salt_hex, hash_hex = almacenado.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


_HASH_FALSO = hash_password("relleno-para-igualar-tiempos")
_intentos = {}  # email -> (fallos, bloqueado_hasta)


def autenticar(db, email: str, password: str):
    """Devuelve el Usuario si las credenciales son válidas; None si no.
    Bloquea temporalmente tras varios intentos fallidos."""
    email = str(email).strip().lower()
    ahora = time.time()
    fallos, hasta = _intentos.get(email, (0, 0.0))
    if hasta > ahora:
        raise PermissionError(
            f"Cuenta bloqueada temporalmente. Reintente en {int(hasta - ahora)} s.")
    datos = db.obtener_credenciales(email) if EMAIL_RE.match(email) else None
    usuario, hash_guardado = datos if datos else (None, _HASH_FALSO)
    ok = verificar_password(password, hash_guardado) and usuario is not None
    if ok:
        _intentos.pop(email, None)
        return usuario
    fallos += 1
    _intentos[email] = (fallos, ahora + BLOQUEO_SEG if fallos >= MAX_INTENTOS else 0.0)
    return None


def cambiar_password(db, usuario, actual: str, nueva: str) -> None:
    """Verifica la contraseña actual y guarda el hash de la nueva."""
    if autenticar(db, usuario.email, actual) is None:
        raise ValidationError("La contraseña actual es incorrecta.")
    nueva = validar_password(nueva)
    if nueva == actual:
        raise ValidationError("La nueva contraseña debe ser distinta de la actual.")
    db.actualizar_password(usuario.id, hash_password(nueva))


def registrar_usuario(db, nombre, email, password, rol="cliente") -> int:
    """Valida, hashea y guarda un usuario nuevo."""
    nombre = validar_texto(nombre, "Nombre", 2, 60)
    email = validar_email(email)
    password = validar_password(password)
    return db.crear_usuario(nombre, email, hash_password(password), rol)


# ---------------------------- Validaciones ----------------------------
def validar_texto(valor, campo="Texto", minimo=1, maximo=100) -> str:
    valor = " ".join(str(valor).split())  # normaliza espacios
    if not minimo <= len(valor) <= maximo:
        raise ValidationError(f"{campo}: debe tener entre {minimo} y {maximo} caracteres.")
    if not TEXTO_RE.match(valor):
        raise ValidationError(f"{campo}: contiene caracteres no permitidos.")
    return valor


def validar_email(valor) -> str:
    valor = str(valor).strip().lower()
    if len(valor) > 120 or not EMAIL_RE.match(valor):
        raise ValidationError("Correo electrónico no válido.")
    return valor


def validar_password(valor) -> str:
    valor = str(valor)
    if not 8 <= len(valor) <= 64:
        raise ValidationError("La contraseña debe tener entre 8 y 64 caracteres.")
    if not (re.search(r"[a-z]", valor) and re.search(r"[A-Z]", valor)
            and re.search(r"\d", valor)):
        raise ValidationError("La contraseña requiere mayúscula, minúscula y número.")
    return valor


def validar_entero(valor, campo="Número", minimo=0, maximo=10_000) -> int:
    texto = str(valor).strip()
    if not re.fullmatch(r"-?\d+", texto):
        raise ValidationError(f"{campo}: debe ser un número entero.")
    n = int(texto)
    if not minimo <= n <= maximo:
        raise ValidationError(f"{campo}: debe estar entre {minimo} y {maximo}.")
    return n


def validar_decimal(valor, campo="Monto", minimo=0.0, maximo=1_000_000.0) -> float:
    try:
        n = float(str(valor).strip().replace(",", "."))
    except ValueError:
        raise ValidationError(f"{campo}: debe ser un número.") from None
    if math.isnan(n) or math.isinf(n) or not minimo <= n <= maximo:
        raise ValidationError(f"{campo}: debe estar entre {minimo} y {maximo}.")
    return round(n, 2)


def validar_fecha(valor, campo="Fecha", futura=False) -> str:
    try:
        f = date.fromisoformat(str(valor).strip())
    except ValueError:
        raise ValidationError(f"{campo}: use el formato AAAA-MM-DD.") from None
    if futura and f < date.today():
        raise ValidationError(f"{campo}: no puede ser una fecha pasada.")
    return f.isoformat()
