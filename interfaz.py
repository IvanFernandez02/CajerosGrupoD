import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time
import random

from config import *
from caja import Caja
from analizador import AnalizadorCajas


class SimulacionApp:
    """Aplicación principal con interfaz Tkinter."""
    
    def __init__(self, root):
        """
        Inicializa la aplicación.
        
        Args:
            root: Ventana principal de Tkinter.
        """
        self.root = root
        self.root.title("🛒 Simulación de Cajas de Supermercado")
        self.root.geometry(f"{ANCHO_PANTALLA}x{ALTO_PANTALLA}")
        self.root.configure(bg=COLOR_FONDO)
        
        self.cajas = []
        self.config = {}
        self.simulacion_corriendo = False
        self.simulacion_terminada = False
        self.ultimo_tiempo = time.time()
        
        self.crear_interfaz_configuracion()
    
    # ===== PANTALLA DE CONFIGURACIÓN =====
    
    def crear_interfaz_configuracion(self):
        """Crea el panel de configuración inicial."""
        self.frame_config = tk.Frame(self.root, bg=COLOR_PANEL, relief=tk.RAISED, bd=2)
        self.frame_config.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=600, height=500)
        
        titulo = tk.Label(
            self.frame_config, 
            text="⚙️ Configuración de la Simulación",
            font=("Arial", 20, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_BOTON
        )
        titulo.pack(pady=20)
        
        frame_campos = tk.Frame(self.frame_config, bg=COLOR_PANEL)
        frame_campos.pack(pady=10, padx=40, fill=tk.BOTH, expand=True)
        
        self.crear_campo(frame_campos, "⏱️ Tiempo escaneo Normal (seg/art):", TIEMPO_ESCANEO_NORMAL, 0)
        self.crear_campo(frame_campos, "⚡ Tiempo escaneo Express (seg/art):", TIEMPO_ESCANEO_EXPRESS, 1)
        self.crear_campo(frame_campos, "💰 Tiempo cobro Mínimo (seg):", TIEMPO_COBRO_MIN, 2)
        self.crear_campo(frame_campos, "💰 Tiempo cobro Máximo (seg):", TIEMPO_COBRO_MAX, 3)
        self.crear_campo(frame_campos, "🏪 Número de cajas Normales:", 3, 4)
        self.crear_campo(frame_campos, "⚡ Número de cajas Express:", 1, 5)
        
        btn_continuar = tk.Button(
            self.frame_config,
            text="Continuar →",
            font=("Arial", 14, "bold"),
            bg=COLOR_BOTON,
            fg="white",
            activebackground=COLOR_BOTON_HOVER,
            cursor="hand2",
            command=self.configurar_cajas,
            padx=20,
            pady=10
        )
        btn_continuar.pack(pady=20)
        
    def crear_campo(self, parent, etiqueta, valor_defecto, fila):
        """Crea un campo de entrada con su etiqueta."""
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.pack(fill=tk.X, pady=8)
        
        label = tk.Label(
            frame,
            text=etiqueta,
            font=("Arial", 11),
            bg=COLOR_PANEL,
            anchor="w",
            width=35
        )
        label.pack(side=tk.LEFT)
        
        entry = tk.Entry(frame, font=("Arial", 11), width=10)
        entry.insert(0, str(valor_defecto))
        entry.pack(side=tk.RIGHT)
        
        setattr(self, f"entry_{fila}", entry)
    
    def configurar_cajas(self):
        """Lee la configuración y pide las filas de cada caja."""
        try:
            self.config = {
                't_scan_normal': float(self.entry_0.get()),
                't_scan_express': float(self.entry_1.get()),
                't_cobro_min': float(self.entry_2.get()),
                't_cobro_max': float(self.entry_3.get()),
                'num_cajas_normales': int(self.entry_4.get()),
                'num_cajas_express': int(self.entry_5.get())
            }
            
            self.frame_config.destroy()
            self.crear_interfaz_filas()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
    
    # ===== PANTALLA DE FILAS =====
    
    def crear_interfaz_filas(self):
        """Interfaz para configurar las filas de cada caja."""
        self.frame_filas = tk.Frame(self.root, bg=COLOR_PANEL, relief=tk.RAISED, bd=2)
        self.frame_filas.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=500, height=550)
        
        titulo = tk.Label(
            self.frame_filas,
            text="👥 Configurar Filas Iniciales",
            font=("Arial", 18, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_BOTON
        )
        titulo.pack(pady=20)
        
        canvas_container = tk.Frame(self.frame_filas, bg=COLOR_PANEL)
        canvas_container.pack(pady=10, padx=30, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        canvas = tk.Canvas(canvas_container, bg=COLOR_PANEL, yscrollcommand=scrollbar.set)
        scrollbar.config(command=canvas.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        frame_interno = tk.Frame(canvas, bg=COLOR_PANEL)
        canvas.create_window((0, 0), window=frame_interno, anchor=tk.NW)
        
        self.entries_filas = []

        # Generar valores aleatorios por defecto (editables) para cada fila.
        # Asumimos rangos razonables: cajas normales 1-20 personas, express 1-20 personas.
        for i in range(self.config['num_cajas_normales']):
            default_val = random.randint(1, 20)
            self.crear_campo_fila(frame_interno, f"🏪 Caja {i+1} (Normal)", i, default_val)

        for i in range(self.config['num_cajas_express']):
            idx = self.config['num_cajas_normales'] + i
            default_val = random.randint(1, 20)
            self.crear_campo_fila(frame_interno, f"⚡ Express {i+1}", idx, default_val)
        
        frame_interno.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        
        btn_iniciar = tk.Button(
            self.frame_filas,
            text="▶️ Iniciar Simulación",
            font=("Arial", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            cursor="hand2",
            command=self.iniciar_simulacion,
            padx=20,
            pady=10
        )
        btn_iniciar.pack(pady=15)
    
    def crear_campo_fila(self, parent, nombre, idx, default_val=None):
        """Crea un campo para configurar personas en fila."""
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.pack(fill=tk.X, pady=5)
        
        label = tk.Label(
            frame,
            text=f"{nombre} - Personas en fila:",
            font=("Arial", 11),
            bg=COLOR_PANEL,
            width=30,
            anchor="w"
        )
        label.pack(side=tk.LEFT, padx=5)
        
        entry = tk.Entry(frame, font=("Arial", 11), width=8)
        # Si se proporciona un valor por defecto (aleatorio), usarlo; si no, usar 0.
        entry.insert(0, str(default_val) if default_val is not None else "0")
        entry.pack(side=tk.RIGHT, padx=5)
        
        self.entries_filas.append(entry)
    
    # ===== CREACIÓN DE CAJAS =====
    
    def iniciar_simulacion(self):
        """Crea las cajas y prepara la simulación."""
        try:
            num_total_cajas = self.config['num_cajas_normales'] + self.config['num_cajas_express']

            # Parametros de layout de la cuadrícula
            box_w = 140
            box_h = 80
            pad_x = 60   # espacio horizontal entre cajas (aumentado)
            pad_y = 280  # espacio vertical entre filas de cajas (aumentado para las filas de clientes)
            top_margin = 80
            
            # Calcular número de columnas que caben en pantalla
            max_columns_by_width = max(1, int((ANCHO_PANTALLA - 80) // (box_w + pad_x)))
            columns = min(num_total_cajas, max_columns_by_width)
            
            # Centrar horizontalmente la cuadrícula
            total_grid_width = columns * box_w + (columns - 1) * pad_x
            left_margin = (ANCHO_PANTALLA - total_grid_width) // 2

            idx_entry = 0
            layout_index = 0

            # Cajas normales
            for i in range(self.config['num_cajas_normales']):
                nombre = f"Caja {i+1}"
                col = layout_index % columns
                row = layout_index // columns
                pos_x = left_margin + col * (box_w + pad_x)
                pos_y = top_margin + row * (box_h + pad_y)

                caja = Caja(nombre, pos_x, pos_y, False, COLOR_CAJA, self.config)

                cantidad = int(self.entries_filas[idx_entry].get())
                caja.agregar_clientes_iniciales(cantidad)
                caja.calcular_tiempo_total_estatico()
                caja.personas_iniciales = len(caja.fila_clientes)
                self.cajas.append(caja)

                idx_entry += 1
                layout_index += 1

            # Cajas express
            for i in range(self.config['num_cajas_express']):
                nombre = f"Express {i+1}"
                col = layout_index % columns
                row = layout_index // columns
                pos_x = left_margin + col * (box_w + pad_x)
                pos_y = top_margin + row * (box_h + pad_y)

                caja = Caja(nombre, pos_x, pos_y, True, COLOR_CAJA_EXPRESS, self.config)

                cantidad = int(self.entries_filas[idx_entry].get())
                caja.agregar_clientes_iniciales(cantidad)
                caja.calcular_tiempo_total_estatico()
                caja.personas_iniciales = len(caja.fila_clientes)
                self.cajas.append(caja)

                idx_entry += 1
                layout_index += 1
            
            self.mostrar_analisis()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese números válidos para las filas")
    
    # ===== PANTALLA DE ANÁLISIS =====
    
    def mostrar_analisis(self):
        """Muestra el análisis de tiempos estáticos."""
        self.frame_filas.destroy()
        
        frame_analisis = tk.Frame(self.root, bg=COLOR_PANEL, relief=tk.RAISED, bd=2)
        frame_analisis.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=700, height=500)
        
        titulo = tk.Label(
            frame_analisis,
            text="📊 Análisis de Tiempos Estáticos",
            font=("Arial", 18, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_BOTON
        )
        titulo.pack(pady=15)
        
        text_area = scrolledtext.ScrolledText(
            frame_analisis,
            font=("Consolas", 10),
            bg="#f9f9f9",
            fg="#333333",
            height=15,
            width=80
        )
        text_area.pack(pady=10, padx=20)
        
        # Generar reporte usando el analizador
        reporte = AnalizadorCajas.generar_reporte_texto(self.cajas)
        text_area.insert(tk.END, reporte)
        text_area.config(state=tk.DISABLED)
        
        btn_ver = tk.Button(
            frame_analisis,
            text="▶️ Ver Simulación Visual",
            font=("Arial", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            cursor="hand2",
            command=lambda: [frame_analisis.destroy(), self.crear_interfaz_simulacion()],
            padx=20,
            pady=10
        )
        btn_ver.pack(pady=15)
    
    # ===== PANTALLA DE SIMULACIÓN =====
    
    def crear_interfaz_simulacion(self):
        """Crea la interfaz de simulación visual."""
        frame_controles = tk.Frame(self.root, bg=COLOR_PANEL, height=50)
        frame_controles.pack(fill=tk.X, padx=10, pady=5)
        
        titulo_sim = tk.Label(
            frame_controles,
            text="🎬 Simulación en Vivo",
            font=("Arial", 16, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_BOTON
        )
        titulo_sim.pack(side=tk.LEFT, padx=10)
        
        self.label_estado = tk.Label(
            frame_controles,
            text="● En ejecución",
            font=("Arial", 12),
            bg=COLOR_PANEL,
            fg="#4CAF50"
        )
        self.label_estado.pack(side=tk.RIGHT, padx=10)
        
        self.canvas = tk.Canvas(
            self.root,
            bg=COLOR_FONDO,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.simulacion_corriendo = True
        self.ultimo_tiempo = time.time()
        self.actualizar_simulacion()
    
    def actualizar_simulacion(self):
        """Bucle principal de actualización de la simulación."""
        if not self.simulacion_corriendo:
            return
        
        tiempo_actual = time.time()
        dt = tiempo_actual - self.ultimo_tiempo
        self.ultimo_tiempo = tiempo_actual
        
        if not self.simulacion_terminada:
            todas_vacias = True
            for caja in self.cajas:
                caja.actualizar(dt)
                if caja.tiene_clientes():
                    todas_vacias = False
            
            if todas_vacias:
                self.simulacion_terminada = True
                self.label_estado.config(text="✓ Simulación Terminada", fg="#F44336")
        
        self.canvas.delete("caja")
        for caja in self.cajas:
            caja.dibujar(self.canvas)
        
        if self.simulacion_terminada:
            self.canvas.create_text(
                ANCHO_PANTALLA // 2, ALTO_PANTALLA // 2,
                text="✅ SIMULACIÓN COMPLETADA\nTodas las cajas están vacías",
                font=("Arial", 24, "bold"),
                fill=COLOR_BOTON,
                tags="caja"
            )
        
        self.root.after(33, self.actualizar_simulacion)  # ~30 FPS
