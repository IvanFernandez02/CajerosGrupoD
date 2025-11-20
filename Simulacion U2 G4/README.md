# 🛒 Simulación de Cajas de Supermercado – Optimización de Costos y SLA

## 👥 Integrantes
- Ivan Fernandez
- Eberson Guayllas
- Juan Alverca
- Ariana Sarango

## 📁 Estructura
```
Simulacion U2 G4/
├── main.py                # Entrada (inicia GUI)
├── interfaz_simulacion.py # Interfaz y exportaciones
├── simulador_colas.py     # Motor M/M/s (réplicas)
├── analizador_costos.py   # Cálculo y agregación de costos
├── cliente.py             # Modelo de cliente
```

## 📄 Módulos
- main.py: arranque de la aplicación.
- interfaz_simulacion.py: configuración, resultados, sensibilidad, conclusiones, exportar PDF/Excel.
- simulador_colas.py: llegadas Poisson, asignación a cajas, métricas por réplica.
- analizador_costos.py: costos (cajas, espera, penalización), promedio y desviación.
- cliente.py: cálculo de tiempo de servicio (escaneo + cobro aleatorio).

## 🔍 Métricas
- Tiempo en sistema promedio
- Tiempo de espera promedio
- % SLA cumplido (bajo umbral)
- Utilización estimada
- Costos: cajas, espera, penalización, total

## 📊 Funcionalidades
- Óptimo de cajas por costo total
- Sensibilidad (λ ±10%, ±20%)
- Regla operativa de apertura
- Reporte ejecutivo y conclusiones
- Exportación a Excel y PDF

## 🚀 Ejecución
```bash
python main.py
```

## 📦 Dependencias
Obligatorias: Python 3.x, tkinter, matplotlib  

Instalación rápida:
```bash
pip install matplotlib reportlab
```

## ⚙️ Parámetros (GUI)
- λ (clientes/min)
- Tiempo de simulación (min)
- Artículos min–max
- Tiempo escaneo y cobro
- Costos (caja, espera, penalización SLA)
- SLA objetivo y umbral (min)
- Máximo de cajas
- Réplicas

## 🧪 Método
- Réplicas independientes (semillas controladas)
- Promedios y desviación estándar
- Selección por menor costo total

## 📤 Exportaciones
- Excel: resumen, configuraciones, réplicas, sensibilidad
- PDF: conclusiones detalladas

