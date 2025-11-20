

import math


class AnalizadorCostos:
    """Analiza costos y determina configuración óptima."""

    @staticmethod
    def calcular_costos(metricas, num_cajas, config):
        """Calcula todos los componentes del costo."""
        tiempo_sim = config["tiempo_simulacion"]

        costo_cajas = config["costo_caja"] * num_cajas * tiempo_sim

        costo_espera = config["costo_espera"] * metricas["tiempo_espera_prom"] * metricas["num_clientes"]

        incumplimiento = max(0, config["sla_objetivo"] - metricas["porcentaje_sla"])
        costo_sla = config["costo_sla"] * incumplimiento

        costo_total = costo_cajas + costo_espera + costo_sla

        return {
            "costo_cajas": costo_cajas,
            "costo_espera": costo_espera,
            "costo_sla": costo_sla,
            "costo_total": costo_total,
        }

    @staticmethod
    def agregar_resultados_replicas(resultados_replicas):
        """Calcula promedios de múltiples réplicas."""
        n = len(resultados_replicas)

        metricas_prom = {
            "num_clientes": sum(r["num_clientes"] for r in resultados_replicas) / n,
            "tiempo_sistema_prom": sum(r["tiempo_sistema_prom"] for r in resultados_replicas) / n,
            "tiempo_espera_prom": sum(r["tiempo_espera_prom"] for r in resultados_replicas) / n,
            "porcentaje_sla": sum(r["porcentaje_sla"] for r in resultados_replicas) / n,
            "utilizacion": sum(r["utilizacion"] for r in resultados_replicas) / n,
        }

        return metricas_prom

    @staticmethod
    def calcular_desviacion(costos_replicas, costo_promedio):
        """Calcula la desviación estándar del costo total."""
        varianza = sum((c["costo_total"] - costo_promedio) ** 2 for c in costos_replicas) / len(costos_replicas)
        return math.sqrt(varianza)
