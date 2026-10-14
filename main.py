"""main.py - Punto de entrada de Viajes Aventura."""
from database import Database


def main():
    db = Database()  # misma BD y misma lógica de seguridad para ambas interfaces
    while True:
        print("\n=== VIAJES AVENTURA ===")
        print("[1] Iniciar en Modo Consola")
        print("[2] Iniciar en Modo Gráfico (GUI - Tkinter)")
        print("[0] Salir")
        op = input("Seleccione una opción: ").strip()
        if op == "1":
            from ui_console import ConsolaApp
            ConsolaApp(db).run()
        elif op == "2":
            try:
                import ui_gui
            except ImportError:
                print("Tkinter no está disponible en este sistema.")
                continue
            ui_gui.run(db)
        elif op == "0":
            break
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    main()
