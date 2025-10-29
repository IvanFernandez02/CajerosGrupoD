"""
Módulo que define la clase Caja.
Representa una caja de cobro con su fila de clientes.
"""

import random
from cliente import Cliente
from config import (
    ARTICULOS_MIN, ARTICULOS_MAX_NORMAL, ARTICULOS_MAX_EXPRESS,
    VELOCIDAD_SIMULACION, COLOR_PERSONA, COLOR_TEXTO
)


class Caja:
    """Representa una caja de cobro y su fila."""
    
    def __init__(self, nombre, x, y, es_express, color, config):
        """
        Inicializa una caja de cobro.
        
        Args:
            nombre: Nombre de la caja (ej: "Caja 1", "Express 1").
            x, y: Posición de la caja en el canvas.
            es_express: Boolean indicando si es caja express.
            color: Color de la caja.
            config: Diccionario con la configuración de tiempos.
        """
        self.nombre = nombre
        self.x = x
        self.y = y
        self.ancho = 140
        self.alto = 80
        self.es_express = es_express
        self.color = color
        self.config = config

        self.fila_clientes = []
        self.cliente_actual = None
        self.tiempo_restante_cliente = 0.0
        self.tiempo_total_estatico = 0.0
        self.personas_iniciales = 0

    def agregar_clientes_iniciales(self, cantidad):
        """
        Añade la cantidad inicial de clientes a la fila.
        
        Args:
            cantidad: Número de clientes a agregar.
        """
        max_articulos = ARTICULOS_MAX_EXPRESS if self.es_express else ARTICULOS_MAX_NORMAL
        tiempo_escaneo = self.config['t_scan_express'] if self.es_express else self.config['t_scan_normal']
        
        for _ in range(cantidad):
            articulos = random.randint(ARTICULOS_MIN, max_articulos)
            cliente = Cliente(
                articulos,
                tiempo_escaneo,
                self.config['t_cobro_min'],
                self.config['t_cobro_max']
            )
            self.fila_clientes.append(cliente)

    def calcular_tiempo_total_estatico(self):
        """
        Calcula el tiempo total necesario para atender a toda la fila.
        
        Returns:
            Tiempo total en segundos.
        """
        if not self.fila_clientes:
            return 0.0
        self.tiempo_total_estatico = sum(c.get_tiempo_atencion() for c in self.fila_clientes)
        return self.tiempo_total_estatico

    def actualizar(self, dt):
        """
        Actualiza la lógica de la caja (procesa clientes).
        
        Args:
            dt: Delta time desde la última actualización.
        """
        if self.cliente_actual:
            self.tiempo_restante_cliente -= dt * VELOCIDAD_SIMULACION
            if self.tiempo_restante_cliente <= 0:
                self.cliente_actual = None
        
        if not self.cliente_actual and self.fila_clientes:
            self.cliente_actual = self.fila_clientes.pop(0)
            self.tiempo_restante_cliente = self.cliente_actual.get_tiempo_atencion()

    def dibujar(self, canvas):
        """
        Dibuja la caja y su fila en el canvas de Tkinter.
        
        Args:
            canvas: Canvas de Tkinter donde dibujar.
        """
        # Dibujar rectángulo de la caja
        canvas.create_rectangle(
            self.x, self.y, self.x + self.ancho, self.y + self.alto,
            fill=self.color, outline="#333333", width=2, tags="caja"
        )
        
        # Nombre de la caja
        canvas.create_text(
            self.x + self.ancho // 2, self.y + 20,
            text=self.nombre, fill="white", 
            font=("Arial", 12, "bold"), tags="caja"
        )

        # Tiempo restante del cliente actual
        if self.cliente_actual:
            tiempo_display = f"{self.tiempo_restante_cliente / VELOCIDAD_SIMULACION:.1f}s"
            canvas.create_text(
                self.x + self.ancho // 2, self.y + 45,
                text=tiempo_display, fill="white", 
                font=("Arial", 10), tags="caja"
            )
            
            # Cliente en la caja (círculo)
            pos_cliente_x = self.x + self.ancho // 2
            pos_cliente_y = self.y + self.alto + 30
            canvas.create_oval(
                pos_cliente_x - 12, pos_cliente_y - 12,
                pos_cliente_x + 12, pos_cliente_y + 12,
                fill=COLOR_PERSONA, outline="#000000", tags="caja"
            )
            
            # Artículos del cliente actual
            canvas.create_text(
                pos_cliente_x + 30, pos_cliente_y,
                text=f"{self.cliente_actual.articulos} art.",
                fill=COLOR_TEXTO, font=("Arial", 9), tags="caja"
            )

        # Dibujar fila de clientes
        for i, cliente in enumerate(self.fila_clientes):
            pos_x = self.x + self.ancho // 2
            pos_y = self.y + self.alto + 30 + ((i + 1) * 35)
            
            # Círculo del cliente
            canvas.create_oval(
                pos_x - 12, pos_y - 12,
                pos_x + 12, pos_y + 12,
                fill=COLOR_PERSONA, outline="#000000", tags="caja"
            )
            
            # Artículos del cliente
            canvas.create_text(
                pos_x + 30, pos_y,
                text=f"{cliente.articulos} art.",
                fill=COLOR_TEXTO, font=("Arial", 9), tags="caja"
            )

        # Número de personas en fila
        canvas.create_text(
            self.x + self.ancho + 60, self.y + 40,
            text=f"Fila: {len(self.fila_clientes)}",
            fill=COLOR_TEXTO, font=("Arial", 11, "bold"), tags="caja"
        )

    def tiene_clientes(self):
        """Retorna True si la caja aún tiene clientes (en atención o en fila)."""
        return self.cliente_actual is not None or len(self.fila_clientes) > 0
