"""Lógica de simulación del sistema de colas."""

import math
import random

from cliente import Cliente


class SimuladorColas:
    """Simulador de sistema de colas M/M/s."""

    def __init__(self, config):
        self.config = config

    def generar_llegadas_poisson(self, lambda_llegadas, tiempo_total):
        """Genera tiempos de llegada según proceso de Poisson."""
        llegadas = []
        tiempo = 0

        while tiempo < tiempo_total:
            # Tiempo entre llegadas: exponencial
            tiempo_entre = -math.log(random.random()) / lambda_llegadas
            tiempo += tiempo_entre
            if tiempo < tiempo_total:
                llegadas.append(tiempo)

        return llegadas

    def simular_replicas(self, num_cajas, num_replicas=20):
        """Ejecuta múltiples réplicas de la simulación."""
        resultados = []

        for replica in range(num_replicas):
            random.seed(replica * 1000)
            resultado = self.simular_una_cola(num_cajas)
            resultados.append(resultado)

        return resultados

    def simular_una_cola(self, num_cajas):
        """Simula una cola M/M/s."""
        lambda_llegadas = self.config["lambda_llegadas"]
        tiempo_simulacion = self.config["tiempo_simulacion"]

        tiempos_llegada = self.generar_llegadas_poisson(lambda_llegadas, tiempo_simulacion)

        clientes = []
        cajas = [0.0] * num_cajas  # Tiempo en que cada caja estará libre

        for tiempo_llegada in tiempos_llegada:
            articulos = random.randint(self.config["articulos_min"], self.config["articulos_max"])

            cliente = Cliente(
                tiempo_llegada,
                articulos,
                self.config["t_scan_normal"],
                self.config["t_cobro_min"],
                self.config["t_cobro_max"],
            )

            caja_disponible = min(range(num_cajas), key=lambda i: cajas[i])
            tiempo_disponible = cajas[caja_disponible]

            cliente.tiempo_inicio_servicio = max(tiempo_llegada, tiempo_disponible)
            cliente.tiempo_fin_servicio = cliente.tiempo_inicio_servicio + cliente.tiempo_servicio
            cliente.tiempo_espera = cliente.tiempo_inicio_servicio - tiempo_llegada
            cliente.tiempo_sistema = cliente.tiempo_fin_servicio - tiempo_llegada

            cajas[caja_disponible] = cliente.tiempo_fin_servicio

            clientes.append(cliente)

        if not clientes:
            return {
                "num_clientes": 0,
                "tiempo_sistema_prom": 0,
                "tiempo_espera_prom": 0,
                "porcentaje_sla": 100,
                "utilizacion": 0,
                "clientes": [],
            }

        tiempo_sistema_prom = sum(c.tiempo_sistema for c in clientes) / len(clientes)
        tiempo_espera_prom = sum(c.tiempo_espera for c in clientes) / len(clientes)

        umbral_tiempo = self.config["umbral_tiempo"]
        clientes_cumplen_sla = sum(1 for c in clientes if c.tiempo_sistema <= umbral_tiempo)
        porcentaje_sla = (clientes_cumplen_sla / len(clientes)) * 100

        tiempo_servicio_total = sum(c.tiempo_servicio for c in clientes)
        utilizacion = (tiempo_servicio_total / (num_cajas * tiempo_simulacion)) * 100

        return {
            "num_clientes": len(clientes),
            "tiempo_sistema_prom": tiempo_sistema_prom,
            "tiempo_espera_prom": tiempo_espera_prom,
            "porcentaje_sla": porcentaje_sla,
            "utilizacion": utilizacion,
            "clientes": clientes,
        }
