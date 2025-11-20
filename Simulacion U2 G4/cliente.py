

import random


class Cliente:
    """Representa un cliente individual en el sistema."""

    def __init__(self, tiempo_llegada, articulos, tiempo_escaneo, tiempo_cobro_min, tiempo_cobro_max):
        self.tiempo_llegada = tiempo_llegada
        self.articulos = articulos
        # Convertir a minutos combinando tiempo de escaneo y cobro aleatorio
        self.tiempo_servicio = (
            articulos * tiempo_escaneo + random.uniform(tiempo_cobro_min, tiempo_cobro_max)
        ) / 60
        self.tiempo_inicio_servicio = 0
        self.tiempo_fin_servicio = 0
        self.tiempo_espera = 0
        self.tiempo_sistema = 0
