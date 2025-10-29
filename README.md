# 🛒 Simulación de Cajas de Supermercado - Grupo D

# Integrantes
  - Ivan Fernandez
  - Eberson Guayllas
  - Juan Alverca
  - Ariana Sarango

```
SimulacionGrupoD/
│
├── main.py          # Punto de entrada de la aplicación
├── interfaz.py      # GUI con Tkinter (todas las pantallas)
├── caja.py          # Clase Caja (lógica de cajas de cobro)
├── cliente.py       # Clase Cliente (clientes individuales)
├── analizador.py    # Análisis estático de tiempos
├── config.py        # Constantes y configuración

```

## 📄 Descripción de Módulos

### `main.py`
- **Propósito**: Punto de entrada del programa
- **Responsabilidad**: Inicializa Tkinter y lanza la aplicación

### `config.py`
- **Propósito**: Configuración centralizada
- **Contiene**:
  - Colores de la interfaz
  - Dimensiones de pantalla
  - Parámetros de simulación por defecto
  - Velocidad de simulación

### `cliente.py`
- **Propósito**: Modelo de datos de un cliente
- **Clase**: `Cliente`
- **Responsabilidad**: 
  - Almacena número de artículos
  - Calcula tiempo de atención total
  - Tiempo de escaneo y cobro

### `caja.py`
- **Propósito**: Lógica de una caja de cobro
- **Clase**: `Caja`
- **Responsabilidad**:
  - Gestiona fila de clientes
  - Procesa clientes (actualización temporal)
  - Renderiza caja y fila en el canvas
  - Calcula tiempos estáticos

### `analizador.py`
- **Propósito**: Análisis comparativo de cajas
- **Clase**: `AnalizadorCajas` (estática)
- **Responsabilidad**:
  - Encuentra la mejor caja (menor tiempo)
  - Compara cajas express vs normales
  - Genera reportes de texto

### `interfaz.py`
- **Propósito**: Interfaz gráfica completa
- **Clase**: `SimulacionApp`
- **Responsabilidad**:
  - Pantalla de configuración inicial
  - Pantalla de configuración de filas
  - Pantalla de análisis estático
  - Pantalla de simulación visual
  - Bucle de actualización (game loop)

## 🚀 Ejecución

```bash
python main.py

## 📦 Dependencias

- Python 3.x
- tkinter (para interfaz gráfica)
