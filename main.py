import tkinter as tk
from interfaz import SimulacionApp


def main():
    root = tk.Tk()
    app = SimulacionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
