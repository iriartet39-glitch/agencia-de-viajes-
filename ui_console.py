"""ui_console.py - Interfaz interactiva por consola."""
from getpass import getpass

import security as sec
from security import ValidationError


def leer(prompt, validador, actual=None):
    """Pide un dato hasta que sea válido. Si hay 'actual', Enter lo conserva."""
    sufijo = f" [{actual}]" if actual is not None else ""
    while True:
        valor = input(f"{prompt}{sufijo}: ").strip()
        if valor == "" and actual is not None:
            return actual
        try:
            return validador(valor)
        except ValidationError as e:
            print(f"  ✖ {e}")


def tabla(encabezados, filas):
    """Imprime una tabla alineada en texto."""
    if not filas:
        print("  (sin registros)")
        return
    filas = [[str(c) for c in f] for f in filas]
    anchos = [max(len(h), *(len(f[i]) for f in filas)) for i, h in enumerate(encabezados)]
    linea = "+-" + "-+-".join("-" * a for a in anchos) + "-+"
    print(linea)
    print("| " + " | ".join(h.ljust(a) for h, a in zip(encabezados, anchos)) + " |")
    print(linea)
    for f in filas:
        print("| " + " | ".join(c.ljust(a) for c, a in zip(f, anchos)) + " |")
    print(linea)


def menu(titulo, opciones):
    """Muestra un menú y devuelve la opción elegida (texto)."""
    print(f"\n=== {titulo} ===")
    for clave, texto in opciones:
        print(f"  [{clave}] {texto}")
    return input("Seleccione una opción: ").strip()


def dinero(x):
    return f"${x:,.2f}"


class ConsolaApp:
    def __init__(self, db):
        self.db = db
        self.usuario = None

    def run(self):
        print("\n✈  VIAJES AVENTURA - Modo Consola")
        while True:
            if self.usuario is None:
                if not self.menu_inicio():
                    print("¡Hasta pronto!")
                    return
            elif self.usuario.es_admin:
                self.menu_admin()
            else:
                self.menu_cliente()

    # ------------------------- acceso -------------------------
    def menu_inicio(self) -> bool:
        op = menu("Bienvenido", [("1", "Iniciar sesión"), ("2", "Registrarse"), ("0", "Salir")])
        if op == "1":
            self.login()
        elif op == "2":
            self.registro()
        elif op == "0":
            return False
        else:
            print("Opción no válida.")
        return True

    def login(self):
        email = input("Correo: ").strip()
        password = getpass("Contraseña: ")
        try:
            usuario = sec.autenticar(self.db, email, password)
        except PermissionError as e:
            print(f"  ✖ {e}")
            return
        if usuario:
            self.usuario = usuario
            print(f"\n✔ Bienvenido/a, {usuario.nombre} ({usuario.rol}).")
        else:
            print("  ✖ Credenciales incorrectas.")

    def registro(self, rol="cliente"):
        nombre = leer("Nombre", lambda v: sec.validar_texto(v, "Nombre", 2, 60))
        email = leer("Correo", sec.validar_email)
        password = leer("Contraseña (8+, mayús., minús., número)",
                        sec.validar_password)
        try:
            sec.registrar_usuario(self.db, nombre, email, password, rol)
            print("✔ Usuario registrado correctamente.")
        except ValueError as e:
            print(f"  ✖ {e}")

    def cambiar_password(self):
        actual = getpass("Contraseña actual: ")
        nueva = getpass("Nueva contraseña (8+, mayús., minús., número): ")
        confirma = getpass("Repita la nueva contraseña: ")
        if nueva != confirma:
            print("  ✖ Las contraseñas no coinciden.")
            return
        try:
            sec.cambiar_password(self.db, self.usuario, actual, nueva)
            print("✔ Contraseña actualizada.")
        except (ValueError, PermissionError) as e:
            print(f"  ✖ {e}")

    # ------------------------- menús -------------------------
    def menu_admin(self):
        op = menu(f"Panel Admin - {self.usuario.nombre}", [
            ("1", "Gestión de destinos"), ("2", "Gestión de paquetes"),
            ("3", "Todas las reservas"), ("4", "Crear usuario administrador"),
            ("5", "Listar usuarios"), ("6", "Cambiar mi contraseña"),
            ("0", "Cerrar sesión")])
        if op == "1":
            self.menu_destinos()
        elif op == "2":
            self.menu_paquetes_admin()
        elif op == "3":
            self.ver_reservas(todas=True)
        elif op == "4":
            self.registro("admin")
        elif op == "5":
            tabla(["ID", "Nombre", "Correo", "Rol"],
                  [(u.id, u.nombre, u.email, u.rol) for u in self.db.listar_usuarios()])
        elif op == "6":
            self.cambiar_password()
        elif op == "0":
            self.usuario = None
        else:
            print("Opción no válida.")

    def menu_cliente(self):
        op = menu(f"Panel Cliente - {self.usuario.nombre}", [
            ("1", "Ver destinos"), ("2", "Ver paquetes"), ("3", "Reservar un paquete"),
            ("4", "Mi historial de reservas"), ("5", "Cancelar una reserva"),
            ("6", "Cambiar mi contraseña"), ("0", "Cerrar sesión")])
        if op == "1":
            self.listar_destinos()
        elif op == "2":
            self.listar_paquetes()
        elif op == "3":
            self.reservar()
        elif op == "4":
            self.ver_reservas()
        elif op == "5":
            self.cancelar()
        elif op == "6":
            self.cambiar_password()
        elif op == "0":
            self.usuario = None
        else:
            print("Opción no válida.")

    # ------------------------- destinos -------------------------
    def listar_destinos(self):
        tabla(["ID", "Nombre", "País", "Costo", "Días"],
              [(d.id, d.nombre, d.pais, dinero(d.costo), d.dias)
               for d in self.db.listar_destinos()])

    def menu_destinos(self):
        op = menu("Destinos", [("1", "Listar"), ("2", "Registrar"), ("3", "Modificar"),
                               ("4", "Eliminar"), ("0", "Volver")])
        if op == "1":
            self.listar_destinos()
        elif op == "2":
            self.datos_destino()
        elif op == "3":
            self.datos_destino(modificar=True)
        elif op == "4":
            self.eliminar_destino()
        elif op != "0":
            print("Opción no válida.")

    def datos_destino(self, modificar=False):
        actual = None
        if modificar:
            self.listar_destinos()
            did = leer("ID del destino", lambda v: sec.validar_entero(v, "ID", 1))
            actual = self.db.obtener_destino(did)
            if not actual:
                print("  ✖ No existe ese destino.")
                return
        g = lambda attr: getattr(actual, attr) if actual else None
        nombre = leer("Nombre", lambda v: sec.validar_texto(v, "Nombre", 2, 60), g("nombre"))
        pais = leer("País", lambda v: sec.validar_texto(v, "País", 2, 60), g("pais"))
        desc = leer("Descripción", lambda v: sec.validar_texto(v, "Descripción", 5, 300),
                    g("descripcion"))
        costo = leer("Costo por persona", lambda v: sec.validar_decimal(v, "Costo", 0, 1e6),
                     g("costo"))
        dias = leer("Días", lambda v: sec.validar_entero(v, "Días", 1, 60), g("dias"))
        if modificar:
            self.db.actualizar_destino(actual.id, nombre, pais, desc, costo, dias)
            print("✔ Destino actualizado.")
        else:
            self.db.crear_destino(nombre, pais, desc, costo, dias)
            print("✔ Destino registrado.")

    def eliminar_destino(self):
        self.listar_destinos()
        did = leer("ID a eliminar", lambda v: sec.validar_entero(v, "ID", 1))
        if input("¿Confirmar eliminación? (s/N): ").strip().lower() != "s":
            return
        try:
            self.db.eliminar_destino(did)
            print("✔ Destino eliminado.")
        except ValueError as e:
            print(f"  ✖ {e}")

    # ------------------------- paquetes -------------------------
    def listar_paquetes(self):
        tabla(["ID", "Paquete", "Inicio", "Fin", "Destinos", "Desc.%", "Costo/pers.", "Cupos libres"],
              [(p.id, p.nombre, p.fecha_inicio, p.fecha_fin,
                ", ".join(d.nombre for d in p.destinos), p.descuento, dinero(p.costo_total),
                f"{p.disponibles}/{p.cupos}")
               for p in self.db.listar_paquetes()])

    def menu_paquetes_admin(self):
        op = menu("Paquetes", [("1", "Listar"), ("2", "Crear"), ("3", "Modificar"),
                               ("4", "Eliminar"), ("0", "Volver")])
        if op == "1":
            self.listar_paquetes()
        elif op == "2":
            self.datos_paquete()
        elif op == "3":
            self.datos_paquete(modificar=True)
        elif op == "4":
            self.listar_paquetes()
            pid = leer("ID a eliminar", lambda v: sec.validar_entero(v, "ID", 1))
            if input("¿Confirmar eliminación? (s/N): ").strip().lower() != "s":
                return
            try:
                self.db.eliminar_paquete(pid)
                print("✔ Paquete eliminado.")
            except ValueError as e:
                print(f"  ✖ {e}")
        elif op != "0":
            print("Opción no válida.")

    def datos_paquete(self, modificar=False):
        actual = None
        if modificar:
            self.listar_paquetes()
            pid = leer("ID del paquete", lambda v: sec.validar_entero(v, "ID", 1))
            actual = self.db.obtener_paquete(pid)
            if not actual:
                print("  ✖ No existe ese paquete.")
                return
        g = lambda attr: getattr(actual, attr) if actual else None
        self.listar_destinos()
        nombre = leer("Nombre del paquete", lambda v: sec.validar_texto(v, "Nombre", 3, 80),
                      g("nombre"))
        inicio = leer("Fecha de inicio (AAAA-MM-DD)",
                      lambda v: sec.validar_fecha(v, "Inicio", futura=True), g("fecha_inicio"))
        desc = leer("Descuento % (0-100)", lambda v: sec.validar_decimal(v, "Descuento", 0, 100),
                    g("descuento"))
        cupos = leer("Cupos (plazas totales)", lambda v: sec.validar_entero(v, "Cupos", 1, 1000),
                     g("cupos") if actual else 20)
        ids = []
        if actual:
            print("  Destinos actuales:", ", ".join(d.nombre for d in actual.destinos))
            if input("¿Cambiar destinos? (s/N): ").strip().lower() != "s":
                ids = [d.id for d in actual.destinos]
        if not ids:
            while True:
                did = leer("ID de destino a añadir (0 = terminar)",
                           lambda v: sec.validar_entero(v, "ID", 0))
                if did == 0:
                    break
                if self.db.obtener_destino(did) is None:
                    print("  ✖ No existe ese destino.")
                elif did in ids:
                    print("  ✖ Ya fue añadido.")
                else:
                    ids.append(did)
        try:
            if actual:
                self.db.actualizar_paquete(actual.id, nombre, inicio, desc, ids, cupos)
                pid = actual.id
                print("✔ Paquete actualizado.")
            else:
                pid = self.db.crear_paquete(nombre, inicio, desc, ids, cupos)
            p = self.db.obtener_paquete(pid)
            print(f"  {p.duracion_dias} días, del {p.fecha_inicio} al {p.fecha_fin}, "
                  f"{dinero(p.costo_total)} por persona, {p.cupos} cupos.")
        except ValueError as e:
            print(f"  ✖ {e}")

    # ------------------------- reservas -------------------------
    def reservar(self):
        self.listar_paquetes()
        pid = leer("ID del paquete", lambda v: sec.validar_entero(v, "ID", 1))
        personas = leer("Número de personas", lambda v: sec.validar_entero(v, "Personas", 1, 50))
        try:
            rid = self.db.crear_reserva(self.usuario.id, pid, personas)
            print(f"✔ Reserva #{rid} confirmada.")
        except ValueError as e:
            print(f"  ✖ {e}")

    def ver_reservas(self, todas=False):
        reservas = self.db.listar_reservas(None if todas else self.usuario.id)
        tabla(["ID", "Cliente", "Paquete", "Personas", "Total", "Estado", "Fecha"],
              [(r.id, r.usuario_nombre, r.paquete_nombre, r.personas, dinero(r.total),
                r.estado, r.fecha_reserva) for r in reservas])

    def cancelar(self):
        self.ver_reservas()
        rid = leer("ID de la reserva a cancelar", lambda v: sec.validar_entero(v, "ID", 1))
        try:
            self.db.cancelar_reserva(rid, self.usuario.id)
            print("✔ Reserva cancelada.")
        except ValueError as e:
            print(f"  ✖ {e}")
