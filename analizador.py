"""
Módulo para el análisis estático de las cajas.
Calcula y compara tiempos de atención.
"""


class AnalizadorCajas:
    """Analiza y compara el rendimiento de las cajas."""
    
    @staticmethod
    def encontrar_mejor_opcion(cajas):
        """
        Encuentra la caja con menor tiempo de espera.
        
        Args:
            cajas: Lista de objetos Caja.
            
        Returns:
            Tupla (mejor_caja, menor_tiempo) o (None, inf) si todas están vacías.
        """
        mejor_opcion = None
        menor_tiempo = float('inf')
        
        for caja in cajas:
            tiempo_total = caja.tiempo_total_estatico
            if tiempo_total < menor_tiempo and caja.personas_iniciales > 0:
                menor_tiempo = tiempo_total
                mejor_opcion = caja
        
        return mejor_opcion, menor_tiempo
    
    @staticmethod
    def comparar_express_vs_normal(cajas):
        """
        Compara el rendimiento de cajas express vs normales.
        
        Args:
            cajas: Lista de objetos Caja.
            
        Returns:
            Diccionario con información de comparación o None si no hay datos suficientes.
        """
        cajas_express = [c for c in cajas if c.es_express and c.personas_iniciales > 0]
        cajas_normales = [c for c in cajas if not c.es_express and c.personas_iniciales > 0]
        
        if not cajas_express or not cajas_normales:
            return None
        
        tiempo_exp = min(c.tiempo_total_estatico for c in cajas_express)
        tiempo_norm = min(c.tiempo_total_estatico for c in cajas_normales)
        
        if tiempo_exp < tiempo_norm:
            resultado = "express_mejor"
        elif tiempo_exp == tiempo_norm:
            resultado = "igual"
        else:
            resultado = "normal_mejor"
        
        return {
            'tiempo_express': tiempo_exp,
            'tiempo_normal': tiempo_norm,
            'resultado': resultado
        }
    
    @staticmethod
    def generar_reporte_texto(cajas):
        """
        Genera un reporte de texto con el análisis completo.
        
        Args:
            cajas: Lista de objetos Caja.
            
        Returns:
            String con el reporte formateado.
        """
        lineas = []
        lineas.append("═" * 70)
        lineas.append("  TIEMPOS TOTALES ESTIMADOS PARA VACIAR CADA FILA")
        lineas.append("═" * 70)
        lineas.append("")
        
        for caja in cajas:
            tipo = "⚡ EXPRESS" if caja.es_express else "🏪 NORMAL"
            lineas.append(f"  {caja.nombre} ({tipo})")
            lineas.append(f"    └─ Personas: {caja.personas_iniciales}")
            lineas.append(f"    └─ Tiempo total: {caja.tiempo_total_estatico:.2f} segundos")
            lineas.append("")
        
        lineas.append("─" * 70)
        mejor_opcion, menor_tiempo = AnalizadorCajas.encontrar_mejor_opcion(cajas)
        if mejor_opcion:
            lineas.append(f"🏆 MEJOR OPCIÓN: {mejor_opcion.nombre}")
            lineas.append(f"   Tiempo estimado: {menor_tiempo:.2f} segundos")
        lineas.append("─" * 70)
        lineas.append("")
        
        # Comparación Express vs Normal
        comparacion = AnalizadorCajas.comparar_express_vs_normal(cajas)
        if comparacion:
            lineas.append("⚖️  COMPARACIÓN EXPRESS vs NORMAL")
            lineas.append(f"   Mejor Express: {comparacion['tiempo_express']:.2f}s")
            lineas.append(f"   Mejor Normal:  {comparacion['tiempo_normal']:.2f}s")
            
            if comparacion['resultado'] == 'express_mejor':
                lineas.append("   ✓ La caja Express ES más eficiente")
            elif comparacion['resultado'] == 'igual':
                lineas.append("   ≈ Ambas tienen la misma eficiencia")
            else:
                lineas.append("   ✗ La caja Express NO es más eficiente")
        
        return "\n".join(lineas)
