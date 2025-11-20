import tkinter as tk

from interfaz_simulacion import InterfazSimulacion


def main():
    """Inicia la aplicación gráfica."""
    root = tk.Tk()
    InterfazSimulacion(root)
    root.mainloop()


if __name__ == "__main__":
    main()
