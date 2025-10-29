import random


class Cliente:
    """Representa a un solo cliente con sus artículos."""
    
    def __init__(self, articulos, tiempo_escaneo, tiempo_cobro_min, tiempo_cobro_max):
        """
        Inicializa un cliente.
        
        Args:
            articulos: Número de artículos que el cliente comprará.
            tiempo_escaneo: Tiempo por artículo en segundos.
            tiempo_cobro_min: Tiempo mínimo de cobro en segundos.
            tiempo_cobro_max: Tiempo máximo de cobro en segundos.
        """
        self.articulos = articulos
        
        # Calcular el tiempo total que este cliente tomará
        self.tiempo_escaneo = self.articulos * tiempo_escaneo
        self.tiempo_cobro = random.uniform(tiempo_cobro_min, tiempo_cobro_max)
        self.tiempo_atencion_total = self.tiempo_escaneo + self.tiempo_cobro

    def get_tiempo_atencion(self):
        """Retorna el tiempo total de atención del cliente."""
        return self.tiempo_atencion_total
