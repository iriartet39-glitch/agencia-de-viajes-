"""models.py - Clases POO del dominio de Viajes Aventura."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List

ROL_ADMIN = "admin"
ROL_CLIENTE = "cliente"


@dataclass
class Usuario:
    """Usuario del sistema. El hash de contraseña NO se guarda aquí."""
    id: int
    nombre: str
    email: str
    rol: str = ROL_CLIENTE

    @property
    def es_admin(self) -> bool:
        return self.rol == ROL_ADMIN


@dataclass
class Destino:
    """Destino turístico individual."""
    id: int
    nombre: str
    pais: str
    descripcion: str
    costo: float  # costo por persona
    dias: int     # duración recomendada


@dataclass
class PaqueteTuristico:
    """Paquete formado por uno o más destinos consecutivos."""
    id: int
    nombre: str
    fecha_inicio: str  # ISO: AAAA-MM-DD
    descuento: float = 0.0  # porcentaje 0-100
    destinos: List[Destino] = field(default_factory=list)
    cupos: int = 20       # plazas totales del paquete
    reservados: int = 0   # plazas ya ocupadas por reservas confirmadas

    @property
    def duracion_dias(self) -> int:
        return sum(d.dias for d in self.destinos)

    @property
    def fecha_fin(self) -> str:
        inicio = date.fromisoformat(self.fecha_inicio)
        dias = max(self.duracion_dias - 1, 0)
        return (inicio + timedelta(days=dias)).isoformat()

    @property
    def disponibles(self) -> int:
        return max(self.cupos - self.reservados, 0)

    @property
    def subtotal(self) -> float:
        return sum(d.costo for d in self.destinos)

    @property
    def costo_total(self) -> float:
        """Costo por persona con el descuento aplicado."""
        return round(self.subtotal * (1 - self.descuento / 100), 2)


@dataclass
class Reserva:
    """Reserva de un cliente sobre un paquete."""
    id: int
    usuario_id: int
    paquete_id: int
    personas: int
    total: float
    estado: str
    fecha_reserva: str
    usuario_nombre: str = ""
    paquete_nombre: str = ""
