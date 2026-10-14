"""ui_gui.py - Interfaz gráfica moderna con Tkinter / ttk."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import security as sec

# Paleta turquesa / azul
BG = "#EAF6F8"
CARD = "#FFFFFF"
DARK = "#0B3C5D"
PRIMARY = "#0B7285"
ACCENT = "#15AABF"
TEXT = "#1F2D3D"
DANGER = "#E03131"
FUENTE = "Segoe UI"

ERRORES = (sec.ValidationError, ValueError, PermissionError)


def dinero(x):
    return f"${x:,.2f}"


def aplicar_estilos(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=BG)
    s.configure(".", font=(FUENTE, 10), background=BG, foreground=TEXT)
    s.configure("TFrame", background=BG)
    s.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1,
                bordercolor="#CFE8EC")
    s.configure("Card.TLabel", background=CARD)
    s.configure("Title.TLabel", font=(FUENTE, 16, "bold"), foreground=PRIMARY, background=CARD)
    s.configure("Head.TLabel", font=(FUENTE, 18, "bold"), foreground="white", background=DARK)
    s.configure("Sub.TLabel", foreground="#CDEBF0", background=DARK)
    s.configure("TEntry", padding=6, fieldbackground="#F7FCFD")
    s.configure("TNotebook", background=CARD, borderwidth=0)
    s.configure("TNotebook.Tab", padding=(16, 8), font=(FUENTE, 10, "bold"))
    for nombre, color, hover in (("Primary", PRIMARY, ACCENT), ("Danger", DANGER, "#C92A2A"),
                                 ("Side", DARK, PRIMARY)):
        s.configure(f"{nombre}.TButton", background=color, foreground="white",
                    font=(FUENTE, 10, "bold"), padding=(14, 8), borderwidth=0)
        s.map(f"{nombre}.TButton", background=[("active", hover)])
    s.configure("Side.TButton", anchor="w", padding=(18, 12))
    s.configure("Treeview", rowheight=30, background=CARD, fieldbackground=CARD,
                bordercolor="#CFE8EC", font=(FUENTE, 10))
    s.configure("Treeview.Heading", background=PRIMARY, foreground="white",
                font=(FUENTE, 10, "bold"), padding=6)
    s.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
    s.map("Treeview.Heading", background=[("active", ACCENT)])


def tarjeta(parent, titulo=None, **grid):
    """Contenedor tipo 'card' con título opcional."""
    f = ttk.Frame(parent, style="Card.TFrame", padding=18)
    if titulo:
        ttk.Label(f, text=titulo, style="Title.TLabel").pack(anchor="w", pady=(0, 10))
    return f


def crear_tabla(parent, columnas):
    """columnas: lista de (id, titulo, ancho). Devuelve (contenedor, treeview)."""
    cont = ttk.Frame(parent, style="Card.TFrame", padding=8)
    tv = ttk.Treeview(cont, columns=[c[0] for c in columnas], show="headings",
                      selectmode="browse")
    for cid, titulo, ancho in columnas:
        tv.heading(cid, text=titulo)
        tv.column(cid, width=ancho, anchor="w")
    sb = ttk.Scrollbar(cont, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tv.tag_configure("par", background="#F1FAFC")
    return cont, tv


def llenar(tv, filas):
    """Rellena un Treeview; el primer valor de cada fila es el iid."""
    tv.delete(*tv.get_children())
    for i, f in enumerate(filas):
        tv.insert("", "end", iid=str(f[0]), values=f, tags=("par",) if i % 2 else ())


def seleccionado(tv):
    sel = tv.selection()
    if not sel:
        raise ValueError("Seleccione un registro de la tabla.")
    return int(sel[0])


def campo(parent, etiqueta, show=None):
    ttk.Label(parent, text=etiqueta, style="Card.TLabel").pack(anchor="w", pady=(6, 0))
    var = tk.StringVar()
    ttk.Entry(parent, textvariable=var, show=show or "").pack(fill="x")
    return var


# ============================ LOGIN / REGISTRO ============================
class LoginFrame(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.contenedor)
        self.app = app
        cab = ttk.Frame(self, style="TFrame")
        cab.pack(fill="x")
        banner = tk.Frame(cab, bg=DARK, height=110)
        banner.pack(fill="x")
        ttk.Label(banner, text="✈  Viajes Aventura", style="Head.TLabel").place(x=40, y=22)
        ttk.Label(banner, text="Descubre el mundo con seguridad", style="Sub.TLabel"
                  ).place(x=44, y=62)

        card = tarjeta(self)
        card.place(relx=0.5, rely=0.55, anchor="center", width=400)
        nb = ttk.Notebook(card)
        nb.pack(fill="both", expand=True)

        t1 = ttk.Frame(nb, style="Card.TFrame", padding=14)
        self.l_email = campo(t1, "Correo electrónico")
        self.l_pass = campo(t1, "Contraseña", show="•")
        ttk.Button(t1, text="Iniciar sesión", style="Primary.TButton",
                   command=self.login).pack(fill="x", pady=(16, 0))
        nb.add(t1, text="Iniciar sesión")

        t2 = ttk.Frame(nb, style="Card.TFrame", padding=14)
        self.r_nombre = campo(t2, "Nombre completo")
        self.r_email = campo(t2, "Correo electrónico")
        self.r_pass = campo(t2, "Contraseña (8+, mayús., minús., número)", show="•")
        ttk.Button(t2, text="Crear cuenta", style="Primary.TButton",
                   command=self.registrar).pack(fill="x", pady=(16, 0))
        nb.add(t2, text="Registrarse")

    def login(self):
        try:
            usuario = sec.autenticar(self.app.db, self.l_email.get(), self.l_pass.get())
        except PermissionError as e:
            return messagebox.showerror("Acceso", str(e))
        if usuario is None:
            return messagebox.showerror("Acceso", "Credenciales incorrectas.")
        self.l_pass.set("")
        self.app.iniciar_sesion(usuario)

    def registrar(self):
        try:
            sec.registrar_usuario(self.app.db, self.r_nombre.get(), self.r_email.get(),
                                  self.r_pass.get())
        except ERRORES as e:
            return messagebox.showerror("Registro", str(e))
        for v in (self.r_nombre, self.r_email, self.r_pass):
            v.set("")
        messagebox.showinfo("Registro", "Cuenta creada. Ya puede iniciar sesión.")


# ============================== VISTAS ==============================
class Vista(ttk.Frame):
    """Base de las pantallas internas."""

    def __init__(self, main):
        super().__init__(main.zona)
        self.main, self.db, self.usuario = main, main.app.db, main.app.usuario
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    def refrescar(self):
        pass


class DestinosVista(Vista):
    def __init__(self, main):
        super().__init__(main)
        col = 0
        if self.usuario.es_admin:
            f = tarjeta(self, "Destino")
            f.grid(row=0, column=0, sticky="ns", padx=(0, 12))
            self.v = {k: campo(f, t) for k, t in (
                ("nombre", "Nombre"), ("pais", "País"), ("descripcion", "Descripción"),
                ("costo", "Costo por persona"), ("dias", "Días"))}
            self.sel_id = None
            for txt, est, cmd in (("Guardar", "Primary", self.guardar),
                                  ("Nuevo", "Side", self.limpiar),
                                  ("Eliminar", "Danger", self.eliminar)):
                ttk.Button(f, text=txt, style=f"{est}.TButton", command=cmd
                           ).pack(fill="x", pady=(10, 0))
            col = 1
        cont, self.tv = crear_tabla(self, [("id", "ID", 40), ("nombre", "Nombre", 160),
                                           ("pais", "País", 110), ("costo", "Costo", 90),
                                           ("dias", "Días", 50), ("desc", "Descripción", 280)])
        cont.grid(row=0, column=1, sticky="nsew")
        if self.usuario.es_admin:
            self.tv.bind("<<TreeviewSelect>>", self.cargar)

    def refrescar(self):
        self.destinos = {d.id: d for d in self.db.listar_destinos()}
        llenar(self.tv, [(d.id, d.nombre, d.pais, dinero(d.costo), d.dias, d.descripcion)
                         for d in self.destinos.values()])

    def cargar(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        d = self.destinos[int(sel[0])]
        self.sel_id = d.id
        for k, val in (("nombre", d.nombre), ("pais", d.pais), ("descripcion", d.descripcion),
                       ("costo", d.costo), ("dias", d.dias)):
            self.v[k].set(val)

    def limpiar(self):
        self.sel_id = None
        for var in self.v.values():
            var.set("")
        self.tv.selection_remove(self.tv.selection())

    def guardar(self):
        try:
            datos = (sec.validar_texto(self.v["nombre"].get(), "Nombre", 2, 60),
                     sec.validar_texto(self.v["pais"].get(), "País", 2, 60),
                     sec.validar_texto(self.v["descripcion"].get(), "Descripción", 5, 300),
                     sec.validar_decimal(self.v["costo"].get(), "Costo", 0, 1e6),
                     sec.validar_entero(self.v["dias"].get(), "Días", 1, 60))
            if self.sel_id:
                self.db.actualizar_destino(self.sel_id, *datos)
            else:
                self.db.crear_destino(*datos)
        except ERRORES as e:
            return messagebox.showerror("Destinos", str(e))
        self.limpiar()
        self.refrescar()

    def eliminar(self):
        try:
            did = seleccionado(self.tv)
            if not messagebox.askyesno("Eliminar", "¿Eliminar el destino seleccionado?"):
                return
            self.db.eliminar_destino(did)
        except ERRORES as e:
            return messagebox.showerror("Destinos", str(e))
        self.limpiar()
        self.refrescar()


class PaquetesVista(Vista):
    def __init__(self, main):
        super().__init__(main)
        self.sel_id = None
        self.paquetes = {}
        f = tarjeta(self, "Paquete" if self.usuario.es_admin else "Reservar")
        f.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        if self.usuario.es_admin:
            self.nombre = campo(f, "Nombre del paquete")
            self.inicio = campo(f, "Fecha de inicio (AAAA-MM-DD)")
            self.desc = campo(f, "Descuento %")
            self.cupos = campo(f, "Cupos (plazas totales)")
            self.desc.set("0")
            self.cupos.set("20")
            ttk.Label(f, text="Destinos (Ctrl+clic para varios)", style="Card.TLabel"
                      ).pack(anchor="w", pady=(6, 0))
            self.lista = tk.Listbox(f, selectmode="extended", height=7, exportselection=False,
                                    relief="flat", highlightthickness=1,
                                    highlightbackground="#CFE8EC", selectbackground=ACCENT)
            self.lista.pack(fill="x")
            ttk.Button(f, text="Guardar paquete", style="Primary.TButton",
                       command=self.guardar).pack(fill="x", pady=(10, 0))
            ttk.Button(f, text="Nuevo", style="Side.TButton",
                       command=self.limpiar).pack(fill="x", pady=(8, 0))
            ttk.Button(f, text="Eliminar seleccionado", style="Danger.TButton",
                       command=self.eliminar).pack(fill="x", pady=(8, 0))
        else:
            ttk.Label(f, text="Seleccione un paquete\nen la tabla y\nelija personas.",
                      style="Card.TLabel").pack(anchor="w")
            self.personas = campo(f, "Número de personas")
            self.personas.set("1")
            ttk.Button(f, text="Reservar ahora", style="Primary.TButton",
                       command=self.reservar).pack(fill="x", pady=(14, 0))
        cont, self.tv = crear_tabla(self, [
            ("id", "ID", 40), ("nombre", "Paquete", 140), ("inicio", "Inicio", 85),
            ("fin", "Fin", 85), ("dias", "Días", 40), ("dest", "Destinos", 170),
            ("desc", "Desc.%", 50), ("total", "Costo/pers.", 90), ("cupos", "Cupos libres", 80)])
        cont.grid(row=0, column=1, sticky="nsew")
        if self.usuario.es_admin:
            self.tv.bind("<<TreeviewSelect>>", self.cargar)

    def refrescar(self):
        paquetes = self.db.listar_paquetes()
        self.paquetes = {p.id: p for p in paquetes}
        llenar(self.tv, [(p.id, p.nombre, p.fecha_inicio, p.fecha_fin, p.duracion_dias,
                          ", ".join(d.nombre for d in p.destinos), p.descuento,
                          dinero(p.costo_total), f"{p.disponibles}/{p.cupos}")
                         for p in paquetes])
        if self.usuario.es_admin:
            self.ids_destinos = []
            self.lista.delete(0, "end")
            for d in self.db.listar_destinos():
                self.ids_destinos.append(d.id)
                self.lista.insert("end", f"{d.nombre} ({d.dias} d, {dinero(d.costo)})")

    def cargar(self, _=None):
        sel = self.tv.selection()
        if not sel:
            return
        p = self.paquetes[int(sel[0])]
        self.sel_id = p.id
        self.nombre.set(p.nombre)
        self.inicio.set(p.fecha_inicio)
        self.desc.set(p.descuento)
        self.cupos.set(p.cupos)
        self.lista.selection_clear(0, "end")
        ids_paquete = {d.id for d in p.destinos}
        for i, did in enumerate(self.ids_destinos):
            if did in ids_paquete:
                self.lista.selection_set(i)

    def limpiar(self):
        self.sel_id = None
        self.nombre.set("")
        self.inicio.set("")
        self.desc.set("0")
        self.cupos.set("20")
        self.lista.selection_clear(0, "end")
        self.tv.selection_remove(self.tv.selection())

    def guardar(self):
        try:
            ids = [self.ids_destinos[i] for i in self.lista.curselection()]
            nombre = sec.validar_texto(self.nombre.get(), "Nombre", 3, 80)
            descuento = sec.validar_decimal(self.desc.get(), "Descuento", 0, 100)
            cupos = sec.validar_entero(self.cupos.get(), "Cupos", 1, 1000)
            if self.sel_id:
                actual = self.paquetes[self.sel_id]
                # solo exige fecha futura si la fecha cambió
                cambio = self.inicio.get().strip() != actual.fecha_inicio
                inicio = sec.validar_fecha(self.inicio.get(), "Inicio", futura=cambio)
                self.db.actualizar_paquete(self.sel_id, nombre, inicio, descuento, ids, cupos)
            else:
                inicio = sec.validar_fecha(self.inicio.get(), "Inicio", futura=True)
                self.db.crear_paquete(nombre, inicio, descuento, ids, cupos)
        except ERRORES as e:
            return messagebox.showerror("Paquetes", str(e))
        self.limpiar()
        self.refrescar()

    def eliminar(self):
        try:
            pid = seleccionado(self.tv)
            if not messagebox.askyesno("Eliminar", "¿Eliminar el paquete seleccionado?"):
                return
            self.db.eliminar_paquete(pid)
        except ERRORES as e:
            return messagebox.showerror("Paquetes", str(e))
        self.limpiar()
        self.refrescar()

    def reservar(self):
        try:
            pid = seleccionado(self.tv)
            n = sec.validar_entero(self.personas.get(), "Personas", 1, 50)
            rid = self.db.crear_reserva(self.usuario.id, pid, n)
        except ERRORES as e:
            return messagebox.showerror("Reservas", str(e))
        messagebox.showinfo("Reservas", f"Reserva #{rid} confirmada.")
        self.refrescar()


class ReservasVista(Vista):
    def __init__(self, main):
        super().__init__(main)
        cont, self.tv = crear_tabla(self, [
            ("id", "ID", 40), ("cliente", "Cliente", 140), ("paquete", "Paquete", 170),
            ("pers", "Personas", 70), ("total", "Total", 100), ("estado", "Estado", 90),
            ("fecha", "Fecha", 130)])
        cont.grid(row=0, column=1, sticky="nsew")
        ttk.Button(self, text="Cancelar reserva seleccionada", style="Danger.TButton",
                   command=self.cancelar).grid(row=1, column=1, sticky="e", pady=(10, 0))

    def refrescar(self):
        rs = self.db.listar_reservas(None if self.usuario.es_admin else self.usuario.id)
        llenar(self.tv, [(r.id, r.usuario_nombre, r.paquete_nombre, r.personas,
                          dinero(r.total), r.estado, r.fecha_reserva) for r in rs])

    def cancelar(self):
        try:
            rid = seleccionado(self.tv)
            self.db.cancelar_reserva(rid, None if self.usuario.es_admin else self.usuario.id)
        except ERRORES as e:
            return messagebox.showerror("Reservas", str(e))
        self.refrescar()


# ============================ PANTALLA PRINCIPAL ============================
class MainFrame(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.contenedor)
        self.app = app
        u = app.usuario
        lateral = tk.Frame(self, bg=DARK, width=220)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        tk.Label(lateral, text="✈ Viajes Aventura", bg=DARK, fg="white",
                 font=(FUENTE, 14, "bold")).pack(pady=(24, 4))
        tk.Label(lateral, text=f"{u.nombre}\n({u.rol})", bg=DARK, fg="#CDEBF0",
                 font=(FUENTE, 9)).pack(pady=(0, 24))
        self.zona = ttk.Frame(self, padding=20)
        self.zona.pack(side="left", fill="both", expand=True)
        self.zona.columnconfigure(0, weight=1)
        self.zona.rowconfigure(1, weight=1)
        self.titulo = ttk.Label(self.zona, font=(FUENTE, 18, "bold"), foreground=DARK)
        self.titulo.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.vistas = {"Destinos": DestinosVista(self), "Paquetes": PaquetesVista(self),
                       "Reservas": ReservasVista(self)}
        etiquetas = {"Destinos": "🌍  Destinos", "Paquetes": "🧳  Paquetes",
                     "Reservas": "📋  Historial de reservas"}
        for nombre, v in self.vistas.items():
            v.grid(row=1, column=0, sticky="nsew")
            ttk.Button(lateral, text=etiquetas[nombre], style="Side.TButton",
                       command=lambda n=nombre: self.mostrar(n)).pack(fill="x")
        ttk.Button(lateral, text="⏻  Cerrar sesión", style="Side.TButton",
                   command=app.cerrar_sesion).pack(side="bottom", fill="x", pady=(0, 16))
        ttk.Button(lateral, text="🔑  Cambiar contraseña", style="Side.TButton",
                   command=self.cambiar_password).pack(side="bottom", fill="x")
        self.mostrar("Destinos")

    def cambiar_password(self):
        actual = simpledialog.askstring("Contraseña", "Contraseña actual:", show="•", parent=self)
        if actual is None:
            return
        nueva = simpledialog.askstring("Contraseña", "Nueva contraseña (8+, mayús., minús., número):",
                                       show="•", parent=self)
        if nueva is None:
            return
        confirma = simpledialog.askstring("Contraseña", "Repita la nueva contraseña:",
                                          show="•", parent=self)
        if nueva != confirma:
            return messagebox.showerror("Contraseña", "Las contraseñas no coinciden.")
        try:
            sec.cambiar_password(self.app.db, self.app.usuario, actual, nueva)
        except ERRORES as e:
            return messagebox.showerror("Contraseña", str(e))
        messagebox.showinfo("Contraseña", "Contraseña actualizada.")

    def mostrar(self, nombre):
        self.titulo.configure(text=nombre)
        v = self.vistas[nombre]
        v.refrescar()
        v.tkraise()


# ================================ APP ================================
class App(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db, self.usuario = db, None
        self.title("Viajes Aventura")
        self.geometry("1100x640")
        self.minsize(960, 560)
        aplicar_estilos(self)
        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill="both", expand=True)
        self.actual = None
        self.mostrar(LoginFrame(self))

    def mostrar(self, frame):
        if self.actual:
            self.actual.destroy()
        self.actual = frame
        frame.pack(fill="both", expand=True)

    def iniciar_sesion(self, usuario):
        self.usuario = usuario
        self.mostrar(MainFrame(self))

    def cerrar_sesion(self):
        self.usuario = None
        self.mostrar(LoginFrame(self))


def run(db):
    App(db).mainloop()
