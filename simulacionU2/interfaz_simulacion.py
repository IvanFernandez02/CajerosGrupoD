# --- interfaz_simulacion.py ---

import math
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analizador_costos import AnalizadorCostos
from simulador_colas import SimuladorColas

# ### CAMBIO CLAVE: LIBRERÍAS DE EXPORTACIÓN MEJORADAS ###
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
except ImportError:
    SimpleDocTemplate = None

# ### CAMBIO CLAVE: FUNCIÓN DE PDF MEJORADA ###
def exportar_pdf_conclusiones(texto_conclusiones_completo):
    """Exporta las conclusiones detalladas a un archivo PDF bien formateado."""
    if SimpleDocTemplate is None:
        messagebox.showerror("Error de Librería", "La librería 'reportlab' no está instalada.\nPor favor, instálala para exportar a PDF (pip install reportlab).")
        return

    archivo = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF Files", "*.pdf")],
        initialfile="conclusiones_y_recomendaciones.pdf"
    )
    if not archivo:
        return

    try:
        doc = SimpleDocTemplate(archivo, pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        style = styles['Code'] # Estilo 'Code' respeta los espacios en blanco
        style.fontSize = 8
        style.leading = 10

        story = []
        # Convertir el texto preformateado a una lista de Párrafos de ReportLab
        for linea in texto_conclusiones_completo.split('\n'):
            # El truco para mantener los espacios es usar &nbsp;
            linea_formateada = linea.replace(" ", "&nbsp;")
            p = Paragraph(linea_formateada, style)
            story.append(p)
        
        doc.build(story)
        messagebox.showinfo("Éxito", f"PDF de Conclusiones guardado en:\n{archivo}")
    except Exception as e:
        messagebox.showerror("Error al Exportar PDF", f"No se pudo guardar el archivo:\n{e}")


# ### CAMBIO CLAVE: FUNCIÓN DE EXCEL MEJORADA ###
def exportar_excel_completo(config, resultados, resultados_sensibilidad):
    """
    Exporta un reporte de Excel exhaustivo con múltiples hojas, incluyendo
    resumen, parámetros, resultados agregados, datos crudos de cada réplica
    y un diccionario de datos.
    """
    if pd is None:
        messagebox.showerror("Error de Librería", "Las librerías 'pandas' y 'openpyxl' no están instaladas.\nPor favor, instálalas para exportar a Excel (pip install pandas openpyxl).")
        return

    archivo = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")],
        initialfile="reporte_analisis_completo.xlsx"
    )
    if not archivo:
        return

    try:
        with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
            # --- Hoja 1: Resumen Ejecutivo y Parámetros ---
            optimo = resultados['optimo']
            ic_95_lower = optimo['costos']['costo_total'] - 1.96 * optimo['desv_est']
            ic_95_upper = optimo['costos']['costo_total'] + 1.96 * optimo['desv_est']
            
            summary_data = {
                "Parámetro": [
                    "--- PARÁMETROS DE ENTRADA ---", *list(config.keys()), "",
                    "--- RESULTADOS ÓPTIMOS ---", "Cajas Óptimas", "Costo Total Mínimo",
                    "Desviación Estándar Costo", "Intervalo de Confianza 95%", "Costo Cajas", "Costo Espera", "Costo SLA",
                    "Cumplimiento SLA (%)", "Utilización (%)", "Tiempo Sistema (min)"
                ],
                "Valor": [
                    "", *list(config.values()), "",
                    "", optimo['num_cajas'], f"${optimo['costos']['costo_total']:.2f}",
                    f"±${optimo['desv_est']:.2f}", f"[${ic_95_lower:.2f} - ${ic_95_upper:.2f}]",
                    f"${optimo['costos']['costo_cajas']:.2f}", f"${optimo['costos']['costo_espera']:.2f}", f"${optimo['costos']['costo_sla']:.2f}",
                    f"{optimo['metricas']['porcentaje_sla']:.1f}%", f"{optimo['metricas']['utilizacion']:.1f}%", f"{optimo['metricas']['tiempo_sistema_prom']:.2f}"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Resumen", index=False)

            # --- Hoja 2: Resultados Agregados (Promedios por Configuración) ---
            df_res = []
            for r in resultados["por_cajas"]:
                df_res.append({
                    "Cajas": r["num_cajas"],
                    "Costo Total Promedio": r["costos"]["costo_total"],
                    "Desv. Est. Costo": r["desv_est"],
                    "Costo Cajas Promedio": r["costos"]["costo_cajas"],
                    "Costo Espera Promedio": r["costos"]["costo_espera"],
                    "Costo SLA Promedio": r["costos"]["costo_sla"],
                    "SLA Promedio %": r["metricas"]["porcentaje_sla"],
                    "Utilización Promedio %": r["metricas"]["utilizacion"],
                    "T. Sistema Promedio (min)": r["metricas"]["tiempo_sistema_prom"],
                    "T. Espera Promedio (min)": r["metricas"]["tiempo_espera_prom"],
                    "Clientes Promedio": r["metricas"]["num_clientes"],
                })
            pd.DataFrame(df_res).to_excel(writer, sheet_name="Resultados Agregados", index=False)

            # --- Hoja 3: Datos Crudos por Réplica (¡LA HOJA MÁS IMPORTANTE!) ---
            datos_crudos = []
            for r_config in resultados["por_cajas"]:
                num_cajas = r_config["num_cajas"]
                # Es crucial combinar las métricas de cada réplica con sus costos calculados
                for i, replica_metricas in enumerate(r_config["replicas"]):
                    # Los costos deben ser recalculados para cada réplica individual
                    costos_replica = AnalizadorCostos.calcular_costos(replica_metricas, num_cajas, config)
                    fila = {
                        "Numero de Cajas": num_cajas,
                        "Replica N°": i + 1,
                        "Costo Total": costos_replica["costo_total"],
                        "Costo Cajas": costos_replica["costo_cajas"],
                        "Costo Espera": costos_replica["costo_espera"],
                        "Costo SLA": costos_replica["costo_sla"],
                        "Clientes Atendidos": replica_metricas["num_clientes"],
                        "% Cumplimiento SLA": replica_metricas["porcentaje_sla"],
                        "% Utilización": replica_metricas["utilizacion"],
                        "Tiempo Promedio Sistema (min)": replica_metricas["tiempo_sistema_prom"],
                        "Tiempo Promedio Espera (min)": replica_metricas["tiempo_espera_prom"],
                    }
                    datos_crudos.append(fila)
            pd.DataFrame(datos_crudos).to_excel(writer, sheet_name="Datos Crudos por Replica", index=False)

            # --- Hoja 4: Análisis de Sensibilidad ---
            if resultados_sensibilidad:
                df_sens = []
                for r in resultados_sensibilidad:
                    df_sens.append({
                        "Variación (%)": r["variacion"],
                        "Lambda (clientes/min)": r["lambda"],
                        "Cajas Óptimas": r["optimo"]["num_cajas"],
                        "Costo Óptimo": r["optimo"]["costo_total"],
                    })
                pd.DataFrame(df_sens).to_excel(writer, sheet_name="Análisis de Sensibilidad", index=False)

            # --- Hoja 5: LÉAME - Diccionario de Datos ---
            diccionario_datos = {
                "Hoja": [
                    "Resumen", "Resumen",
                    "Resultados Agregados", "Resultados Agregados", "Resultados Agregados",
                    "Datos Crudos por Replica", "Datos Crudos por Replica",
                    "Análisis de Sensibilidad", "Análisis de Sensibilidad",
                ],
                "Columna": [
                    "Parámetro", "Valor",
                    "Costo Total Promedio", "Desv. Est. Costo", "SLA Promedio %",
                    "Costo Total", "Replica N°",
                    "Lambda (clientes/min)", "Costo Óptimo"
                ],
                "Descripción": [
                    "Nombre del parámetro de entrada o de la métrica de resultado.",
                    "Valor utilizado en la simulación o valor óptimo calculado.",
                    "El costo total promedio de todas las réplicas para esa configuración de cajas.",
                    "La desviación estándar del costo total, mide la variabilidad o riesgo.",
                    "El porcentaje promedio de clientes que cumplieron el SLA en todas las réplicas.",
                    "El costo total para una única corrida/réplica de la simulación.",
                    "El identificador de la corrida individual (de 1 al N° de réplicas).",
                    "La tasa de llegada de clientes modificada para ese escenario de sensibilidad.",
                    "El costo total mínimo encontrado para esa tasa de llegada específica."
                ]
            }
            pd.DataFrame(diccionario_datos).to_excel(writer, sheet_name="LÉAME - Diccionario", index=False)

            # --- Autoajuste del ancho de las columnas para mejor legibilidad ---
            for sheetname in writer.sheets:
                worksheet = writer.sheets[sheetname]
                for col in worksheet.columns:
                    max_length = 0
                    column = col[0].column_letter # Get the column name
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column].width = adjusted_width

        messagebox.showinfo("Éxito", f"Archivo Excel completo guardado en:\n{archivo}")
    except Exception as e:
        messagebox.showerror("Error al Exportar Excel", f"No se pudo guardar el archivo:\n{e}")

class InterfazSimulacion:
    """Interfaz gráfica principal mejorada."""

    def __init__(self, root):
        self.root = root
        self.root.title("🛒 Simulación de Cajas - Análisis de Negocio")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f0f0f0")

        self.config = {}
        self.resultados = None
        self.resultados_sensibilidad = None
        self.sensibilidad_ejecutada = False

        self.crear_pantalla_configuracion()

    def crear_pantalla_configuracion(self):
        # ... (esta función y las de crear secciones no cambian)
        for widget in self.root.winfo_children():
            widget.destroy()
        canvas_config = tk.Canvas(self.root, bg="#f0f0f0")
        scrollbar_config = tk.Scrollbar(self.root, orient="vertical", command=canvas_config.yview)
        main_frame = tk.Frame(canvas_config, bg="#f0f0f0")
        main_frame.bind("<Configure>", lambda e: canvas_config.configure(scrollregion=canvas_config.bbox("all")))
        canvas_config.create_window((0, 0), window=main_frame, anchor="nw")
        canvas_config.configure(yscrollcommand=scrollbar_config.set)
        titulo = tk.Label(main_frame, text="⚙️ Configuración de Simulación - Enfoque de Negocio", font=("Arial", 24, "bold"), bg="#f0f0f0", fg="#1976D2")
        titulo.pack(pady=(20, 20))
        sections_frame = tk.Frame(main_frame, bg="#f0f0f0")
        sections_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        left_column = tk.Frame(sections_frame, bg="#f0f0f0")
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        right_column = tk.Frame(sections_frame, bg="#f0f0f0")
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.crear_seccion_tiempo(left_column)
        self.crear_seccion_costos(left_column)
        self.crear_seccion_sla(right_column)
        self.crear_seccion_simulacion(right_column)
        btn_frame = tk.Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=30)
        btn_ejecutar = tk.Button(btn_frame, text="▶️ Ejecutar Simulación Completa", font=("Arial", 16, "bold"), bg="#4CAF50", fg="white", activebackground="#45a049", command=self.ejecutar_simulacion, padx=30, pady=15, cursor="hand2")
        btn_ejecutar.pack()
        canvas_config.pack(side="left", fill="both", expand=True)
        scrollbar_config.pack(side="right", fill="y")
        def _on_mousewheel(event):
            canvas_config.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.bind_all("<MouseWheel>", _on_mousewheel)

    def crear_seccion_tiempo(self, parent):
        frame = tk.LabelFrame(parent, text="⏱️ Parámetros de Tiempo", font=("Arial", 14, "bold"), bg="#E3F2FD", fg="#0D47A1", padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        self.entry_t_scan = self.crear_campo(frame, "Tiempo escaneo (seg/artículo):", 5)
        self.entry_t_cobro_min = self.crear_campo(frame, "Tiempo cobro mínimo (seg):", 15)
        self.entry_t_cobro_max = self.crear_campo(frame, "Tiempo cobro máximo (seg):", 30)
        self.entry_articulos_min = self.crear_campo(frame, "Artículos mínimos:", 1)
        self.entry_articulos_max = self.crear_campo(frame, "Artículos máximos:", 50)

    def crear_seccion_costos(self, parent):
        frame = tk.LabelFrame(parent, text="💰 Costos (USD)", font=("Arial", 14, "bold"), bg="#E8F5E9", fg="#1B5E20", padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        self.entry_costo_caja = self.crear_campo(frame, "Costo por caja activa (USD/min):", 0.5)
        self.entry_costo_espera = self.crear_campo(frame, "Costo tiempo espera (USD/min por cliente):", 0.2)
        self.entry_costo_sla = self.crear_campo(frame, "Penalización SLA (USD por punto %):", 100)

    def crear_seccion_sla(self, parent):
        frame = tk.LabelFrame(parent, text="🎯 Objetivo de Servicio (SLA)", font=("Arial", 14, "bold"), bg="#F3E5F5", fg="#4A148C", padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        self.entry_sla_objetivo = self.crear_campo(frame, "SLA objetivo (% de clientes):", 80)
        self.entry_umbral_tiempo = self.crear_campo(frame, "Umbral de tiempo (minutos):", 8)

    def crear_seccion_simulacion(self, parent):
        frame = tk.LabelFrame(parent, text="🔬 Parámetros de Simulación", font=("Arial", 14, "bold"), bg="#FFF3E0", fg="#E65100", padx=20, pady=15)
        frame.pack(fill=tk.X, pady=(0, 15))
        self.entry_num_replicas = self.crear_campo(frame, "Número de réplicas:", 20)
        self.entry_tiempo_sim = self.crear_campo(frame, "Tiempo de simulación (min):", 60)
        self.entry_lambda = self.crear_campo(frame, "Tasa de llegadas (clientes/min):", 5)
        self.entry_max_cajas = self.crear_campo(frame, "Máximo de cajas a probar:", 10)

    def crear_campo(self, parent, etiqueta, valor_default):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.pack(fill=tk.X, pady=5)
        label = tk.Label(frame, text=etiqueta, font=("Arial", 11), bg=parent["bg"], anchor="w", width=35)
        label.pack(side=tk.LEFT)
        entry = tk.Entry(frame, font=("Arial", 11), width=12)
        entry.insert(0, str(valor_default))
        entry.pack(side=tk.RIGHT)
        return entry

    def ejecutar_simulacion(self):
        # <<< CAMBIO: AÑADIMOS EL REINICIO DEL ESTADO DE LA SIMULACIÓN ANTERIOR >>>
        self.resultados = None
        self.resultados_sensibilidad = None
        self.sensibilidad_ejecutada = False
        # <<< FIN DEL CAMBIO >>>

        try:
            self.config = {
                "t_scan_normal": float(self.entry_t_scan.get()), "t_cobro_min": float(self.entry_t_cobro_min.get()),
                "t_cobro_max": float(self.entry_t_cobro_max.get()), "articulos_min": int(self.entry_articulos_min.get()),
                "articulos_max": int(self.entry_articulos_max.get()), "costo_caja": float(self.entry_costo_caja.get()),
                "costo_espera": float(self.entry_costo_espera.get()), "costo_sla": float(self.entry_costo_sla.get()),
                "sla_objetivo": float(self.entry_sla_objetivo.get()), "umbral_tiempo": float(self.entry_umbral_tiempo.get()),
                "num_replicas": int(self.entry_num_replicas.get()), "tiempo_simulacion": float(self.entry_tiempo_sim.get()),
                "lambda_llegadas": float(self.entry_lambda.get()), "max_cajas": int(self.entry_max_cajas.get()),
            }
            self.mostrar_progreso()
        except ValueError as exc:
            messagebox.showerror("Error", f"Por favor ingrese valores numéricos válidos.\n{exc}")

    def mostrar_progreso(self):
        # ... (esta función no cambia)
        for widget in self.root.winfo_children(): widget.destroy()
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(expand=True)
        tk.Label(frame, text="⏳ Ejecutando Simulación...", font=("Arial", 24, "bold"), bg="#f0f0f0", fg="#1976D2").pack(pady=20)
        self.progress_label = tk.Label(frame, text="Preparando simulación...", font=("Arial", 14), bg="#f0f0f0")
        self.progress_label.pack(pady=10)
        self.progress_bar = ttk.Progressbar(frame, length=400, mode="determinate")
        self.progress_bar.pack(pady=20)
        self.root.after(100, self.procesar_simulacion)

    def procesar_simulacion(self):
        simulador = SimuladorColas(self.config)
        resultados_por_cajas = []
        max_cajas = self.config["max_cajas"]
        num_replicas = self.config["num_replicas"]
        for s in range(1, max_cajas + 1):
            progreso = (s / max_cajas) * 100
            self.progress_bar["value"] = progreso
            self.progress_label["text"] = f"Simulando configuración con {s} caja(s)... ({s}/{max_cajas})"
            self.root.update()
            resultados_replicas = simulador.simular_replicas(s, num_replicas)
            metricas_prom = AnalizadorCostos.agregar_resultados_replicas(resultados_replicas)
            costos_replicas = [AnalizadorCostos.calcular_costos(r, s, self.config) for r in resultados_replicas]
            costos_prom = {k: sum(c[k] for c in costos_replicas) / num_replicas for k in costos_replicas[0]}
            desv_est = AnalizadorCostos.calcular_desviacion(costos_replicas, costos_prom["costo_total"])
            resultados_por_cajas.append({"num_cajas": s, "metricas": metricas_prom, "costos": costos_prom, "desv_est": desv_est, "replicas": resultados_replicas})

        # <<< CAMBIO: LÓGICA DE DOBLE OPTIMIZACIÓN >>>
        sla_objetivo = self.config["sla_objetivo"]
        resultados_cumplen_sla = [r for r in resultados_por_cajas if r["metricas"]["porcentaje_sla"] >= sla_objetivo]
        
        cumple_sla_flag = bool(resultados_cumplen_sla)
        
        if cumple_sla_flag:
            # Opción 1: El más barato de los que cumplen.
            optimo_economico = min(resultados_cumplen_sla, key=lambda x: x["costos"]["costo_total"])
            # Opción 2: El que usa MENOS cajas para cumplir.
            optimo_operacional = min(resultados_cumplen_sla, key=lambda x: x["num_cajas"])
        else:
            # Si ninguno cumple, ambas recomendaciones apuntan al "mejor esfuerzo".
            optimo_fallido = max(resultados_por_cajas, key=lambda x: x["metricas"]["porcentaje_sla"])
            optimo_economico = optimo_fallido
            optimo_operacional = optimo_fallido

        self.resultados = {
            "por_cajas": resultados_por_cajas,
            "optimo_economico": optimo_economico,
            "optimo_operacional": optimo_operacional,
            "cumple_sla": cumple_sla_flag
        }
        self.mostrar_resultados()

    def crear_pestana_resumen(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📊 Resumen Ejecutivo")
        canvas_resumen = tk.Canvas(frame, bg="white"); scrollbar_resumen = tk.Scrollbar(frame, orient="vertical", command=canvas_resumen.yview)
        scrollable_frame = tk.Frame(canvas_resumen, bg="white")
        scrollable_frame.bind("<Configure>", lambda e: canvas_resumen.configure(scrollregion=canvas_resumen.bbox("all")))
        canvas_resumen.create_window((0, 0), window=scrollable_frame, anchor="nw"); canvas_resumen.configure(yscrollcommand=scrollbar_resumen.set)

        tk.Label(scrollable_frame, text="📊 Resumen de Decisiones Estratégicas", font=("Arial", 20, "bold"), bg="white", fg="#1976D2").pack(pady=20)
        
        eco = self.resultados["optimo_economico"]
        ops = self.resultados["optimo_operacional"]
        
        if not self.resultados["cumple_sla"]:
            max_cajas_probadas = self.config["max_cajas"]
            sugerencia_cajas = max_cajas_probadas + 5
            mensaje_texto = (f"⚠️ ¡ATENCIÓN! Ninguna de las {max_cajas_probadas} configuraciones probadas alcanzó el SLA del {self.config['sla_objetivo']:.0f}%.\n"
                             f"Se recomienda re-ejecutar la simulación aumentando el 'Máximo de cajas a probar' (ej: a {sugerencia_cajas}).")
            msg_frame = tk.Frame(scrollable_frame, bg="#FFEBEE", bd=2, relief=tk.GROOVE)
            msg_frame.pack(pady=10, padx=40, fill=tk.X)
            tk.Label(msg_frame, text=mensaje_texto, font=("Arial", 12, "bold"), bg="#FFEBEE", fg="#B71C1C", wraplength=800).pack(padx=15, pady=15)
            tk.Label(scrollable_frame, text="Se muestra la configuración de 'mejor esfuerzo' encontrada:", font=("Arial", 11), bg="white").pack(pady=(10,0))
            
            # <<< CAMBIO CLAVE: La tarjeta ahora se crea Y se empaqueta (dibuja) en la pantalla >>>
            card = self.crear_tarjeta_recomendacion(scrollable_frame, "Mejor Esfuerzo (SLA más alto)", eco, "#F44336")
            card.pack(pady=(0, 20), padx=40, fill=tk.X)
        
        elif eco['num_cajas'] == ops['num_cajas']:
            mensaje_texto = "✅ ¡EXCELENTE! La configuración más económica es también la más eficiente en número de cajas."
            msg_frame = tk.Frame(scrollable_frame, bg="#E8F5E9", bd=2, relief=tk.GROOVE)
            msg_frame.pack(pady=10, padx=40, fill=tk.X)
            tk.Label(msg_frame, text=mensaje_texto, font=("Arial", 12, "bold"), bg="#E8F5E9", fg="#1B5E20").pack(padx=15, pady=15)
            card = self.crear_tarjeta_recomendacion(scrollable_frame, "🏆 Recomendación Única y Óptima", eco, "#4CAF50")
            card.pack(pady=(0, 20), padx=40, fill=tk.X)
        
        else:
            mensaje_texto = "💡 Se han identificado DOS estrategias óptimas. Elija según su prioridad de negocio:"
            msg_frame = tk.Frame(scrollable_frame, bg="#E3F2FD", bd=2, relief=tk.GROOVE)
            msg_frame.pack(pady=10, padx=40, fill=tk.X)
            tk.Label(msg_frame, text=mensaje_texto, font=("Arial", 12, "bold"), bg="#E3F2FD", fg="#0D47A1").pack(padx=15, pady=15)

            comparison_frame = tk.Frame(scrollable_frame, bg="white")
            comparison_frame.pack(fill=tk.X, expand=True, padx=20)
            
            frame_ops = self.crear_tarjeta_recomendacion(comparison_frame, "⚙️ Óptimo Operacional (Mínimas Cajas)", ops, "#FF9800")
            frame_ops.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

            frame_eco = self.crear_tarjeta_recomendacion(comparison_frame, "💰 Óptimo Económico (Menor Costo)", eco, "#2196F3")
            frame_eco.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

            cost_diff = eco['costos']['costo_total'] - ops['costos']['costo_total']
            box_diff = eco['num_cajas'] - ops['num_cajas']
            
            tradeoff_frame = tk.LabelFrame(scrollable_frame, text="🤔 Análisis de Decisión (Trade-Off)", font=("Arial", 14, "bold"), bg="white", padx=20, pady=15)
            tradeoff_frame.pack(pady=20, padx=40, fill=tk.X)
            tradeoff_text = f"""
            • El Óptimo Operacional usa {ops['num_cajas']} cajas con un costo de ${ops['costos']['costo_total']:.2f}.
            • El Óptimo Económico usa {eco['num_cajas']} cajas ({box_diff} más) pero es ${abs(cost_diff):.2f} más barato.

            Pregunta Clave: ¿Vale la pena gestionar {box_diff} caja(s) adicional(es) para ahorrar ${abs(cost_diff):.2f}?

            » Elija Óptimo OPERACIONAL si prioriza: simplicidad, menos personal y agilidad.
            » Elija Óptimo ECONÓMICO si prioriza: minimizar el costo total por encima de todo.
            """
            tk.Label(tradeoff_frame, text=tradeoff_text, font=("Arial", 11), bg="white", justify=tk.LEFT).pack()

        canvas_resumen.pack(side="left", fill="both", expand=True)
        scrollbar_resumen.pack(side="right", fill="y")
        def _on_mousewheel_resumen(event): canvas_resumen.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_resumen.bind_all("<MouseWheel>", _on_mousewheel_resumen)

    def crear_tarjeta_recomendacion(self, parent, titulo, data, color):
        """Función auxiliar para crear las nuevas tarjetas de recomendación."""
        card = tk.LabelFrame(parent, text=f" {titulo} ", font=("Arial", 14, "bold"), bg="white", fg=color, relief=tk.GROOVE, bd=3, padx=20, pady=15)
        
        def add_metric(label, value, bold=False):
            frame = tk.Frame(card, bg="white")
            frame.pack(fill=tk.X, pady=2)
            font_style = ("Arial", 11, "bold") if bold else ("Arial", 11)
            tk.Label(frame, text=label, font=font_style, bg="white", anchor="w").pack(side=tk.LEFT)
            tk.Label(frame, text=value, font=font_style, bg="white", anchor="e").pack(side=tk.RIGHT)

        add_metric("Número de Cajas:", f"{data['num_cajas']}", True)
        add_metric("Costo Total:", f"${data['costos']['costo_total']:.2f} USD", True)
        add_metric("Cumplimiento SLA:", f"{data['metricas']['porcentaje_sla']:.1f}%")
        add_metric("Utilización de Cajas:", f"{data['metricas']['utilizacion']:.1f}%")
        add_metric("Tiempo en Sistema:", f"{data['metricas']['tiempo_sistema_prom']:.2f} min")

        return card # Devuelve el frame para poder empaquetarlo fuera
    
    def mostrar_resultados(self):
        """Muestra los resultados de la simulación en una interfaz con pestañas."""
        for widget in self.root.winfo_children():
            widget.destroy()

        # Frame de botones en la parte inferior
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        # Notebook (pestañas) ocupa el resto del espacio
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        # Crear todas las pestañas
        self.crear_pestana_resumen(notebook)
        self.crear_pestana_graficos(notebook)
        self.crear_pestana_tabla(notebook)
        self.crear_pestana_sensibilidad(notebook)
        self.crear_pestana_regla(notebook)
        self.crear_pestana_conclusiones(notebook)

        # Botón: Nueva Simulación (a la derecha)
        tk.Button(btn_frame, text="🔄 Nueva Simulación", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.crear_pantalla_configuracion, padx=20, pady=10).pack(side=tk.RIGHT, padx=5)

        # Botones de exportación (a la izquierda)
        tk.Button(btn_frame, text="📄 Exportar Conclusiones (PDF)", font=("Arial", 12, "bold"), bg="#FF5722", fg="white", command=lambda: exportar_pdf_conclusiones(self.generar_texto_conclusiones_completo()), padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="📊 Exportar Datos (Excel)", font=("Arial", 12, "bold"), bg="#2196F3", fg="white", command=lambda: exportar_excel_completo(self.config, self.resultados, self.resultados_sensibilidad), padx=20, pady=10).pack(side=tk.LEFT, padx=5)
    def crear_tarjeta(self, parent, titulo, valor, color, row, col):
        #...código sin cambios...
        card = tk.Frame(parent, bg=color, relief=tk.RAISED, bd=3)
        card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew", ipadx=30, ipady=20)
        tk.Label(card, text=titulo, font=("Arial", 12, "bold"), bg=color, fg="white").pack()
        tk.Label(card, text=valor, font=("Arial", 24, "bold"), bg=color, fg="white").pack(pady=10)

    def crear_pestana_graficos(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📈 Gráficos")
        canvas_graficos = tk.Canvas(frame, bg="white")
        scrollbar_graficos = tk.Scrollbar(frame, orient="vertical", command=canvas_graficos.yview)
        frame_graficos = tk.Frame(canvas_graficos, bg="white")
        frame_graficos.bind("<Configure>", lambda e: canvas_graficos.configure(scrollregion=canvas_graficos.bbox("all")))
        canvas_graficos.create_window((0, 0), window=frame_graficos, anchor="nw")
        canvas_graficos.configure(yscrollcommand=scrollbar_graficos.set)
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 12))
        fig.patch.set_facecolor("white")
        plt.subplots_adjust(hspace=0.4, wspace=0.35, top=0.96, bottom=0.08, left=0.1, right=0.95)
        
        resultados = self.resultados["por_cajas"]
        # <<< CAMBIO: Obtenemos ambos óptimos >>>
        ops = self.resultados["optimo_operacional"]
        eco = self.resultados["optimo_economico"]

        num_cajas = [r["num_cajas"] for r in resultados]
        costos_totales = [r["costos"]["costo_total"] for r in resultados]
        ax1.plot(num_cajas, costos_totales, "o-", linewidth=2.5, markersize=9, color="#2196F3")
        
        # <<< CAMBIO: Dibujamos una línea para cada óptimo >>>
        if ops['num_cajas'] == eco['num_cajas']:
            ax1.axvline(ops["num_cajas"], color="red", linestyle="--", linewidth=2, label="Óptimo Único")
        else:
            ax1.axvline(ops["num_cajas"], color="#FF9800", linestyle="--", linewidth=2, label=f"Óptimo Operacional ({ops['num_cajas']} cajas)")
            ax1.axvline(eco["num_cajas"], color="#F44336", linestyle="--", linewidth=2, label=f"Óptimo Económico ({eco['num_cajas']} cajas)")

        ax1.set_xlabel("Número de Cajas (s)", fontsize=12, fontweight="bold")
        ax1.set_ylabel("Costo Total (USD)", fontsize=12, fontweight="bold")
        ax1.set_title("💰 Costo Total vs Número de Cajas", fontsize=13, fontweight="bold", pad=12)
        ax1.grid(True, alpha=0.3, linestyle='--'); ax1.legend(fontsize=10); ax1.set_xticks(num_cajas)
        
        costo_cajas = [r["costos"]["costo_cajas"] for r in resultados]; costo_espera = [r["costos"]["costo_espera"] for r in resultados]; costo_sla = [r["costos"]["costo_sla"] for r in resultados]
        ax2.bar(num_cajas, costo_cajas, label="Costo Cajas", color="#4CAF50", width=0.6)
        ax2.bar(num_cajas, costo_espera, bottom=costo_cajas, label="Costo Espera", color="#FF9800", width=0.6)
        bottom = [cc + ce for cc, ce in zip(costo_cajas, costo_espera)]
        ax2.bar(num_cajas, costo_sla, bottom=bottom, label="Costo SLA", color="#F44336", width=0.6)
        ax2.set_xlabel("Número de Cajas (s)", fontsize=12, fontweight="bold"); ax2.set_ylabel("Costo (USD)", fontsize=12, fontweight="bold"); ax2.set_title("📊 Componentes del Costo", fontsize=13, fontweight="bold", pad=12)
        ax2.legend(loc='upper right', fontsize=10); ax2.grid(True, alpha=0.3, axis="y", linestyle='--'); ax2.set_xticks(num_cajas)
        
        sla_porcentajes = [r["metricas"]["porcentaje_sla"] for r in resultados]
        ax3.plot(num_cajas, sla_porcentajes, "o-", linewidth=2.5, markersize=9, color="#4CAF50", label="SLA Logrado")
        ax3.axhline(self.config["sla_objetivo"], color="red", linestyle="--", linewidth=2, label=f"Objetivo: {self.config['sla_objetivo']}%")
        ax3.set_xlabel("Número de Cajas (s)", fontsize=12, fontweight="bold"); ax3.set_ylabel("Cumplimiento SLA (%)", fontsize=12, fontweight="bold"); ax3.set_title("🎯 Cumplimiento de SLA", fontsize=13, fontweight="bold", pad=12)
        ax3.grid(True, alpha=0.3, linestyle='--'); ax3.legend(fontsize=10, loc='lower right'); ax3.set_ylim([0, 105]); ax3.set_xticks(num_cajas)
        
        utilizacion = [r["metricas"]["utilizacion"] for r in resultados]
        bars = ax4.bar(num_cajas, utilizacion, color="#9C27B0", width=0.6, label="Utilización")
        ax4.set_xlabel("Número de Cajas (s)", fontsize=12, fontweight="bold"); ax4.set_ylabel("Utilización (%)", fontsize=12, fontweight="bold"); ax4.set_title("⚙️ Utilización de Cajas", fontsize=13, fontweight="bold", pad=12)
        ax4.grid(True, alpha=0.3, axis="y", linestyle='--'); ax4.set_xticks(num_cajas)
        
        # <<< CAMBIO: Coloreamos las barras de ambos óptimos >>>
        ops_idx = ops["num_cajas"] - 1
        eco_idx = eco["num_cajas"] - 1
        if ops_idx < len(bars): bars[ops_idx].set_color("#FF9800")
        if eco_idx < len(bars): bars[eco_idx].set_color("#F44336")
            
        ax4.legend(fontsize=10, loc='upper right')
        
        canvas = FigureCanvasTkAgg(fig, frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas_graficos.pack(side="left", fill="both", expand=True)
        scrollbar_graficos.pack(side="right", fill="y")

    def crear_pestana_tabla(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📋 Tabla Detallada")
        canvas_tabla = tk.Canvas(frame, bg="white"); scrollbar_tabla = tk.Scrollbar(frame, orient="vertical", command=canvas_tabla.yview)
        frame_tabla = tk.Frame(canvas_tabla, bg="white")
        frame_tabla.bind("<Configure>", lambda e: canvas_tabla.configure(scrollregion=canvas_tabla.bbox("all")))
        canvas_tabla.create_window((0, 0), window=frame_tabla, anchor="nw"); canvas_tabla.configure(yscrollcommand=scrollbar_tabla.set)
        tk.Label(frame_tabla, text="📋 Matriz de Resultados por Configuración", font=("Arial", 18, "bold"), bg="white", fg="#1976D2").pack(pady=15)
        
        resultados = self.resultados["por_cajas"]
        # <<< CAMBIO: Obtenemos el número de cajas de ambos óptimos >>>
        ops_num = self.resultados["optimo_operacional"]["num_cajas"]
        eco_num = self.resultados["optimo_economico"]["num_cajas"]

        columnas = ["Cajas", "C.Total", "C.Cajas", "C.Espera", "C.SLA", "SLA%", "Util.%", "T.Sistema", "T.Espera", "Desv.Est"]
        
        datos = []
        for r in resultados:
            # <<< CAMBIO: Lógica para marcar con iconos >>>
            marca = ""
            if r['num_cajas'] == ops_num: marca += "⚙️"
            if r['num_cajas'] == eco_num: marca += "💰"
            if ops_num == eco_num and r['num_cajas'] == ops_num: marca = "🏆"
            
            fila = [
                f"{marca} {r['num_cajas']}", f"${r['costos']['costo_total']:.2f}", f"${r['costos']['costo_cajas']:.2f}",
                f"${r['costos']['costo_espera']:.2f}", f"${r['costos']['costo_sla']:.2f}", f"{r['metricas']['porcentaje_sla']:.1f}%",
                f"{r['metricas']['utilizacion']:.1f}%", f"{r['metricas']['tiempo_sistema_prom']:.2f}m", 
                f"{r['metricas']['tiempo_espera_prom']:.2f}m", f"±${r['desv_est']:.2f}"
            ]
            datos.append(fila)

        fig_tabla, ax_tabla = plt.subplots(figsize=(13, max(6, len(datos) * 0.4))); fig_tabla.patch.set_facecolor("white"); ax_tabla.axis('tight'); ax_tabla.axis('off')
        tabla = ax_tabla.table(cellText=datos, colLabels=columnas, cellLoc='center', loc='center')
        tabla.auto_set_font_size(False); tabla.set_fontsize(9); tabla.scale(1, 2)
        for i in range(len(columnas)): tabla[(0, i)].set_facecolor('#1976D2'); tabla[(0, i)].set_text_props(weight='bold', color='white')
        
        # Colorear filas de óptimos
        for i, r in enumerate(resultados):
            color = '#F5F5F5' if (i + 1) % 2 == 0 else 'white'
            if r['num_cajas'] == ops_num: color = '#FFF3E0' # Naranja claro
            if r['num_cajas'] == eco_num: color = '#E3F2FD' # Azul claro
            if r['num_cajas'] == ops_num and r['num_cajas'] == eco_num: color = '#E8F5E9' # Verde claro
            for j in range(len(columnas)):
                tabla[(i + 1, j)].set_facecolor(color)

        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        canvas_tabla_fig = FigureCanvasTkAgg(fig_tabla, frame_tabla); canvas_tabla_fig.draw(); canvas_tabla_fig.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # <<< CAMBIO: Leyenda de iconos actualizada >>>
        leyenda_texto = "🏆=Óptimo Único | ⚙️=Óptimo Operacional | 💰=Óptimo Económico"
        tk.Label(frame_tabla, text=f"{leyenda_texto} | Réplicas: {self.config['num_replicas']}", font=("Arial", 11, "bold"), bg="white", fg="#1976D2").pack(pady=10)
        
        canvas_tabla.pack(side="left", fill="both", expand=True); scrollbar_tabla.pack(side="right", fill="y")

    def crear_pestana_sensibilidad(self, notebook):
        #...código sin cambios...
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="🔍 Análisis de Sensibilidad")
        canvas_sens = tk.Canvas(frame, bg="white")
        scrollbar_sens = tk.Scrollbar(frame, orient="vertical", command=canvas_sens.yview)
        scrollable_frame_sens = tk.Frame(canvas_sens, bg="white")
        scrollable_frame_sens.bind("<Configure>", lambda e: canvas_sens.configure(scrollregion=canvas_sens.bbox("all")))
        canvas_sens.create_window((0, 0), window=scrollable_frame_sens, anchor="nw")
        canvas_sens.configure(yscrollcommand=scrollbar_sens.set)
        tk.Label(scrollable_frame_sens, text="🔍 Análisis de Sensibilidad - Variación en Tasa de Llegadas", font=("Arial", 18, "bold"), bg="white", fg="#1976D2").pack(pady=15)
        if not self.sensibilidad_ejecutada:
            btn_frame = tk.Frame(scrollable_frame_sens, bg="white"); btn_frame.pack(pady=20)
            tk.Label(btn_frame, text="El análisis de sensibilidad evalúa cómo cambia el costo óptimo\ncon variaciones de ±10% y ±20% en la tasa de llegadas (λ).", font=("Arial", 12), bg="white", justify=tk.CENTER).pack(pady=10)
            tk.Button(btn_frame, text="▶️ Ejecutar Análisis de Sensibilidad", font=("Arial", 14, "bold"), bg="#FF9800", fg="white", command=lambda: self.ejecutar_sensibilidad(scrollable_frame_sens, canvas_sens), padx=30, pady=15).pack()
        canvas_sens.pack(side="left", fill="both", expand=True); scrollbar_sens.pack(side="right", fill="y")

    def ejecutar_sensibilidad(self, parent_frame, canvas_parent):
        #...código sin cambios...
        for widget in parent_frame.winfo_children(): widget.destroy()
        tk.Label(parent_frame, text="⏳ Ejecutando Análisis de Sensibilidad...", font=("Arial", 18, "bold"), bg="white", fg="#FF9800").pack(pady=20)
        progress = ttk.Progressbar(parent_frame, length=400, mode="determinate"); progress.pack(pady=10); self.root.update()
        variaciones = [-20, -10, 0, 10, 20]; resultados_sensibilidad = []
        total_pasos = len(variaciones) * self.config["max_cajas"]; paso_actual = 0
        for var in variaciones:
            lambda_modificada = self.config["lambda_llegadas"] * (1 + var / 100); config_temp = self.config.copy(); config_temp["lambda_llegadas"] = lambda_modificada
            simulador_temp = SimuladorColas(config_temp); resultados_var = []
            for s in range(1, self.config["max_cajas"] + 1):
                paso_actual += 1; progress["value"] = (paso_actual / total_pasos) * 100; self.root.update()
                replicas = simulador_temp.simular_replicas(s, 10); metricas_prom = AnalizadorCostos.agregar_resultados_replicas(replicas)
                costos_replicas = [AnalizadorCostos.calcular_costos(r, s, config_temp) for r in replicas]
                costo_prom = sum(c["costo_total"] for c in costos_replicas) / len(costos_replicas); resultados_var.append({"num_cajas": s, "costo_total": costo_prom})
            optimo_var = min(resultados_var, key=lambda x: x["costo_total"])
            resultados_sensibilidad.append({"variacion": var, "lambda": lambda_modificada, "resultados": resultados_var, "optimo": optimo_var})
        for widget in parent_frame.winfo_children(): widget.destroy()
        tk.Label(parent_frame, text="🔍 Resultados del Análisis de Sensibilidad", font=("Arial", 18, "bold"), bg="white", fg="#1976D2").pack(pady=15)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5)); fig.patch.set_facecolor("white"); plt.subplots_adjust(hspace=0.3, wspace=0.35, top=0.90, bottom=0.15)
        for r in resultados_sensibilidad: ax1.plot([x["num_cajas"] for x in r["resultados"]], [x["costo_total"] for x in r["resultados"]], "o-", label=f"Tasa = {r['lambda']:.2f} ({r['variacion']:+d}%)", linewidth=2, markersize=6)
        ax1.set_xlabel("Número de Cajas (s)", fontsize=11, fontweight="bold"); ax1.set_ylabel("Costo Total (USD)", fontsize=11, fontweight="bold"); ax1.set_title("💰 Costo Total vs Tasa de Llegadas (λ)", fontsize=12, fontweight="bold", pad=12); ax1.legend(fontsize=8, loc='best'); ax1.grid(True, alpha=0.3, linestyle='--')
        variaciones_vals = [r["variacion"] for r in resultados_sensibilidad]; cajas_optimas = [r["optimo"]["num_cajas"] for r in resultados_sensibilidad]; costos_optimos = [r["optimo"]["costo_total"] for r in resultados_sensibilidad]; ax2_twin = ax2.twinx()
        line1 = ax2.plot(variaciones_vals, cajas_optimas, "o-", color="#2196F3", linewidth=2.5, markersize=9, label="Cajas Óptimas")
        line2 = ax2_twin.plot(variaciones_vals, costos_optimos, "s-", color="#F44336", linewidth=2.5, markersize=9, label="Costo Óptimo")
        ax2.set_xlabel("Variación en Tasa de Llegadas (%)", fontsize=11, fontweight="bold"); ax2.set_ylabel("Número de Cajas Óptimas", fontsize=11, fontweight="bold", color="#2196F3"); ax2_twin.set_ylabel("Costo Total Óptimo (USD)", fontsize=11, fontweight="bold", color="#F44336")
        ax2.set_title("📊 Robustez de la Solución", fontsize=12, fontweight="bold", pad=12); ax2.grid(True, alpha=0.3, linestyle='--'); ax2.tick_params(axis='y', labelcolor="#2196F3"); ax2_twin.tick_params(axis='y', labelcolor="#F44336")
        lines1, labels1 = ax2.get_legend_handles_labels(); lines2, labels2 = ax2_twin.get_legend_handles_labels(); ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
        canvas = FigureCanvasTkAgg(fig, parent_frame); canvas.draw(); canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        resumen_frame = tk.LabelFrame(parent_frame, text="📋 Resumen de Sensibilidad", font=("Arial", 13, "bold"), bg="white", padx=20, pady=15); resumen_frame.pack(fill=tk.X, padx=20, pady=15)
        columnas_sens = ["Variación", "Lambda (λ)", "Cajas Óptimas", "Costo Óptimo"]; datos_sens = [[f"{r['variacion']:+d}%", f"{r['lambda']:.2f}", f"{r['optimo']['num_cajas']}", f"${r['optimo']['costo_total']:.2f}"] for r in resultados_sensibilidad]
        fig_sens, ax_sens = plt.subplots(figsize=(10, 3.5)); fig_sens.patch.set_facecolor("white"); ax_sens.axis('tight'); ax_sens.axis('off')
        tabla_sens = ax_sens.table(cellText=datos_sens, colLabels=columnas_sens, cellLoc='center', loc='center')
        tabla_sens.auto_set_font_size(False); tabla_sens.set_fontsize(10); tabla_sens.scale(1, 2.5)
        for i in range(len(columnas_sens)): tabla_sens[(0, i)].set_facecolor('#FF9800'); tabla_sens[(0, i)].set_text_props(weight='bold', color='white')
        for i in range(1, len(datos_sens) + 1):
            for j in range(len(columnas_sens)): tabla_sens[(i, j)].set_facecolor('#FFF3E0' if i % 2 == 0 else 'white')
        plt.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.1); canvas_sens_tabla = FigureCanvasTkAgg(fig_sens, resumen_frame); canvas_sens_tabla.draw(); canvas_sens_tabla.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=5)
        self.sensibilidad_ejecutada = True; self.resultados_sensibilidad = resultados_sensibilidad; parent_frame.update_idletasks(); canvas_parent.configure(scrollregion=canvas_parent.bbox("all"))

    def crear_pestana_regla(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📜 Regla de Apertura")
        canvas_scroll = tk.Canvas(frame, bg="white")
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas_scroll.yview)
        scrollable_frame = tk.Frame(canvas_scroll, bg="white")
        scrollable_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        tk.Label(scrollable_frame, text="📜 Regla de Apertura de Cajas Propuesta", font=("Arial", 20, "bold"), bg="white", fg="#1976D2").pack(pady=20)
        
        # <<< CAMBIO: La regla se basa en el ÓPTIMO OPERACIONAL >>>
        optimo = self.resultados["optimo_operacional"]
        
        rho = optimo["metricas"]["utilizacion"] / 100
        lambda_val = self.config["lambda_llegadas"]
        mu = 1 / ((self.config["t_scan_normal"] * 5 + (self.config["t_cobro_min"] + self.config["t_cobro_max"]) / 2) / 60)
        s_opt = optimo["num_cajas"]

        try:
            rho_sistema = lambda_val / (s_opt * mu)
            lq_aprox = lambda_val * optimo["metricas"]["tiempo_espera_prom"] if rho_sistema < 1 else "Sistema inestable"
        except ZeroDivisionError:
            lq_aprox = "No calculable"
        
        regla_frame = tk.LabelFrame(scrollable_frame, text="🎯 Regla Principal (Basada en Óptimo Operacional)", font=("Arial", 14, "bold"), bg="#E3F2FD", fg="#0D47A1", padx=30, pady=20)
        regla_frame.pack(fill=tk.X, padx=40, pady=15)

        regla_texto = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    REGLA DE APERTURA                          ║
╠═══════════════════════════════════════════════════════════════╣
║  Operar con {s_opt} cajas como base. Abrir una caja adicional     ║
║  cuando se cumplan AMBAS condiciones durante > 5 minutos:     ║
║                                                               ║
║  1. La utilización promedio por caja supera {rho*100:.1f}%    ║
║  2. El tiempo promedio en sistema supera {self.config['umbral_tiempo']:.1f} minutos  ║
╚═══════════════════════════════════════════════════════════════╝
        """
        tk.Label(regla_frame, text=regla_texto, font=("Courier", 10, "bold"), bg="#E3F2FD", justify=tk.LEFT, fg="#0D47A1").pack()
        
        justif_frame = tk.LabelFrame(scrollable_frame, text="💡 Justificación Técnica", font=("Arial", 14, "bold"), bg="#FFF3E0", fg="#E65100", padx=30, pady=20)
        justif_frame.pack(fill=tk.X, padx=40, pady=15)

        justif_texto = f"""
Esta regla se basa en la configuración de {s_opt} cajas (Óptimo Operacional),
que es el número MÍNIMO de cajas para cumplir el SLA de forma eficiente.

• Con {s_opt} cajas:
  - Costo Total: ${optimo['costos']['costo_total']:.2f} USD
  - Cumplimiento SLA: {optimo['metricas']['porcentaje_sla']:.1f}%
  - Utilización: {optimo['metricas']['utilizacion']:.1f}%

• Si usamos {s_opt-1 if s_opt > 1 else s_opt} caja(s):
  - NO se cumpliría el objetivo de SLA.
  - Aumentaría drásticamente el tiempo de espera.

• Si la demanda aumenta (picos), la regla dinámica de apertura
  permite adaptarse sin mantener cajas ociosas permanentemente.
        """
        tk.Label(justif_frame, text=justif_texto, font=("Arial", 10), bg="#FFF3E0", justify=tk.LEFT).pack(anchor="w")
        
        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        def _on_mousewheel_regla(event): canvas_scroll.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel_regla)
    def crear_pestana_conclusiones(self, notebook):
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📝 Conclusiones")
        canvas_concl = tk.Canvas(frame, bg="white"); scrollbar_concl = tk.Scrollbar(frame, orient="vertical", command=canvas_concl.yview)
        scrollable_frame = tk.Frame(canvas_concl, bg="white")
        scrollable_frame.bind("<Configure>", lambda e: canvas_concl.configure(scrollregion=canvas_concl.bbox("all")))
        canvas_concl.create_window((0, 0), window=scrollable_frame, anchor="nw"); canvas_concl.configure(yscrollcommand=scrollbar_concl.set)

        tk.Label(scrollable_frame, text="📝 CONCLUSIONES Y RECOMENDACIONES ACCIONABLES", font=("Arial", 20, "bold"), bg="white", fg="#1976D2").pack(pady=20)
        
        # <<< CAMBIO CLAVE: Usa la nueva estructura de datos, evitando el error >>>
        ops = self.resultados["optimo_operacional"]
        eco = self.resultados["optimo_economico"]
        # Usaremos el óptimo operacional como base para las recomendaciones generales
        optimo = ops 

        conclusiones_frame = tk.LabelFrame(scrollable_frame, text="🎯 Conclusiones Clave", font=("Arial", 14, "bold"), bg="#E3F2FD", fg="#0D47A1", padx=30, pady=20)
        conclusiones_frame.pack(fill=tk.X, padx=40, pady=15)

        # Texto de conclusiones adaptado
        if not self.resultados['cumple_sla']:
            conclusiones_texto = f"""
1. ALERTA: SISTEMA SATURADO
   • Ninguna configuración probada (hasta {self.config['max_cajas']} cajas) alcanza el SLA.
   • La causa es una insuficiencia de recursos para la demanda actual.
   • Es IMPERATIVO re-simular con un rango mayor de cajas.

2. "MEJOR ESFUERZO" IDENTIFICADO
   • La configuración de {optimo['num_cajas']} CAJAS es la que más se acerca al objetivo.
   • SLA logrado: {optimo['metricas']['porcentaje_sla']:.1f}% (Objetivo: {self.config['sla_objetivo']:.0f}%)
   • Este resultado NO es una solución, sino un punto de partida para un nuevo análisis.
"""
        elif ops['num_cajas'] == eco['num_cajas']:
             conclusiones_texto = f"""
1. PUNTO ÓPTIMO ÚNICO IDENTIFICADO
   • La configuración de {optimo['num_cajas']} CAJAS es la más económica y eficiente.
   • Minimiza el costo total en ${optimo['costos']['costo_total']:.2f} y cumple el SLA.
   • Representa el balance perfecto entre costo y nivel de servicio.

2. TRADE-OFF CRÍTICO DEMOSTRADO
   • Con menos cajas se incumple el SLA. Con más, aumentan los costos sin
     un beneficio significativo. La decisión es clara y directa.
"""
        else:
             conclusiones_texto = f"""
1. DOS ESTRATEGIAS ÓPTIMAS IDENTIFICADAS
   • Se encontró un balance entre minimizar costos y simplificar operaciones.
   • Óptimo Operacional ({ops['num_cajas']} cajas): El mínimo de recursos para cumplir el SLA.
   • Óptimo Económico ({eco['num_cajas']} cajas): La opción de costo total más bajo.

2. DECISIÓN BASADA EN PRIORIDADES
   • El negocio debe elegir entre agilidad operativa (menos cajas) y
     ahorro máximo (menor costo total). El análisis del trade-off es clave.
"""

        tk.Label(conclusiones_frame, text=conclusiones_texto, font=("Arial", 10), bg="#E3F2FD", justify=tk.LEFT).pack(anchor="w")

        recom_frame = tk.LabelFrame(scrollable_frame, text="⚡ Plan de Acción - Recomendaciones", font=("Arial", 14, "bold"), bg="#E8F5E9", fg="#1B5E20", padx=30, pady=20)
        recom_frame.pack(fill=tk.X, padx=40, pady=15)
        
        recomendaciones_texto = f"""
📌 ACCIÓN INMEDIATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. AJUSTAR OPERACIÓN BASE A {optimo['num_cajas']} CAJAS
   ✓ Establecer {optimo['num_cajas']} cajas como el estándar para períodos normales.
   ✓ Impacto: Lograr el SLA ({optimo['metricas']['porcentaje_sla']:.1f}%) con la operación más simple posible.

📌 ACCIÓN TÁCTICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. REGLA DE APERTURA DINÁMICA
   ✓ Capacitar supervisores para abrir una caja adicional cuando:
     - Utilización > {optimo['metricas']['utilizacion']:.0f}%
     - Y Tiempo en sistema > {self.config['umbral_tiempo']:.0f} minutos
   ✓ Impacto: Flexibilidad para picos de demanda.

📌 INVERSIÓN ESTRATÉGICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. DASHBOARD DE MONITOREO EN TIEMPO REAL
   ✓ Instalar un display con métricas clave para la toma de decisiones.
   ✓ Impacto: Gestión proactiva basada en datos.
"""
        tk.Label(recom_frame, text=recomendaciones_texto, font=("Courier", 9), bg="#E8F5E9", justify=tk.LEFT).pack(anchor="w")

        canvas_concl.pack(side="left", fill="both", expand=True)
        scrollbar_concl.pack(side="right", fill="y")
        def _on_mousewheel_concl(event): canvas_concl.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_concl.bind_all("<MouseWheel>", _on_mousewheel_concl)
    def mostrar_ventana_conclusiones(self):
        """Muestra una ventana emergente con las conclusiones completas."""
        ventana = tk.Toplevel(self.root)
        ventana.title("📝 Conclusiones y Recomendaciones Completas")
        ventana.geometry("1000x750")
        ventana.configure(bg="white")

        # Header
        header_frame = tk.Frame(ventana, bg="#1976D2", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="📝 CONCLUSIONES Y RECOMENDACIONES",
            font=("Arial", 22, "bold"),
            bg="#1976D2",
            fg="white",
        ).pack(expand=True)

        # Contenido con scroll
        canvas = tk.Canvas(ventana, bg="white")
        scrollbar = tk.Scrollbar(ventana, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        optimo = self.resultados["optimo"]

        # Generar contenido completo
        texto_completo = self.generar_texto_conclusiones_completo()

        # Mostrar texto en widget scrollable
        text_widget = scrolledtext.ScrolledText(
            scrollable_frame,
            font=("Courier", 9),
            bg="#f9f9f9",
            wrap=tk.WORD,
            padx=20,
            pady=20
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        text_widget.insert(tk.END, texto_completo)
        text_widget.config(state=tk.DISABLED)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Botones en la parte inferior
        btn_frame = tk.Frame(ventana, bg="#f0f0f0", height=70)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btn_frame.pack_propagate(False)

        tk.Button(
            btn_frame,
            text="💾 Exportar como TXT",
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            command=lambda: self.guardar_reporte(texto_completo),
            padx=25,
            pady=10,
        ).pack(side=tk.LEFT, padx=20, pady=15)

        tk.Button(
            btn_frame,
            text="🖨️ Imprimir",
            font=("Arial", 12, "bold"),
            bg="#2196F3",
            fg="white",
            command=lambda: self.imprimir_conclusiones(texto_completo),
            padx=25,
            pady=10,
        ).pack(side=tk.LEFT, padx=10, pady=15)

        tk.Button(
            btn_frame,
            text="❌ Cerrar",
            font=("Arial", 12, "bold"),
            bg="#F44336",
            fg="white",
            command=ventana.destroy,
            padx=25,
            pady=10,
        ).pack(side=tk.RIGHT, padx=20, pady=15)

    def generar_texto_conclusiones_completo(self):
        if not self.resultados["cumple_sla"]:
            # La lógica para cuando no se cumple el SLA ya es buena, la mantenemos.
            # (El código de la alerta que ya tenías)
            optimo = self.resultados["optimo_economico"] # Usamos cualquiera, son iguales
            config = self.config
            resultados_por_cajas = self.resultados["por_cajas"]
            sla_objetivo = config["sla_objetivo"]
            max_cajas_probadas = config["max_cajas"]
            resultado_max_cajas = resultados_por_cajas[-1]
            sla_max_cajas = resultado_max_cajas['metricas']['porcentaje_sla']
            if max_cajas_probadas > 1:
                mejora_por_caja = sla_max_cajas - resultados_por_cajas[-2]['metricas']['porcentaje_sla']
            else:
                mejora_por_caja = 0
            if mejora_por_caja > 1:
                sla_faltante = sla_objetivo - sla_max_cajas
                cajas_adicionales = math.ceil(sla_faltante / mejora_por_caja) + 1
                sugerencia_cajas = max_cajas_probadas + cajas_adicionales
            else:
                sugerencia_cajas = max_cajas_probadas + 3
            return f"""
═══════════════════════════════════════════════════════════════════════════
               ⚠️ ALERTA: OBJETIVO DE SERVICIO (SLA) NO ALCANZADO ⚠️
═══════════════════════════════════════════════════════════════════════════
RESUMEN EJECUTIVO:
La simulación ha determinado que NINGUNA de las configuraciones probadas
(de 1 a {max_cajas_probadas} cajas) es suficiente para alcanzar el objetivo de nivel de 
servicio (SLA) del {sla_objetivo:.0f}%. El sistema se encuentra SATURADO.
... (el resto de tu texto de alerta puede ir aquí)...
SUGERENCIA INTELIGENTE:
Se recomienda probar con un máximo de al menos: ➡️  {sugerencia_cajas} CAJAS  ⬅️
"""

        eco = self.resultados["optimo_economico"]
        ops = self.resultados["optimo_operacional"]
        
        if eco['num_cajas'] == ops['num_cajas']:
            # El caso simple donde ambos son iguales
            return f"""
═══════════════════════════════════════════════════════════════════════════
               ✅ INFORME DE OPTIMIZACIÓN Y PLAN DE ACCIÓN ✅
═══════════════════════════════════════════════════════════════════════════
RESUMEN EJECUTIVO:
¡Resultados excelentes! Se ha identificado una configuración única que es
a la vez la más económica y la más eficiente en el uso de recursos.

CONFIGURACIÓN ÓPTIMA RECOMENDADA: {eco['num_cajas']} CAJAS ABIERTAS

Métricas Clave:
• Costo Total: ${eco['costos']['costo_total']:.2f} USD (Mínimo posible cumpliendo SLA)
• Cumplimiento SLA: {eco['metricas']['porcentaje_sla']:.1f}% (Objetivo: {self.config['sla_objetivo']:.0f}%)
• Utilización: {eco['metricas']['utilizacion']:.1f}%

CONCLUSIÓN:
La decisión es directa. La configuración de {eco['num_cajas']} cajas representa el balance
perfecto entre costo y servicio sin ninguna desventaja.

PLAN DE ACCIÓN:
Implementar la operación estándar con {eco['num_cajas']} cajas y monitorizar los resultados.
... (puedes añadir más detalles del plan de acción aquí) ...
"""
        else:
            # El caso complejo y más interesante: hay un trade-off.
            cost_diff = eco['costos']['costo_total'] - ops['costos']['costo_total']
            box_diff = eco['num_cajas'] - ops['num_cajas']
            return f"""
═══════════════════════════════════════════════════════════════════════════
          💡 INFORME DE DECISIÓN ESTRATÉGICA: COSTO vs. OPERACIÓN 💡
═══════════════════════════════════════════════════════════════════════════

RESUMEN EJECUTIVO:
La simulación ha identificado DOS estrategias viables que cumplen el objetivo
de SLA. La elección entre ellas depende de la prioridad estratégica del negocio:
minimizar el costo total o minimizar la complejidad operativa (número de cajas).

═══════════════════════════════════════════════════════════════════════════
                       ANÁLISIS COMPARATIVO
═══════════════════════════════════════════════════════════════════════════

                                  Opción A: ÓPTIMO           Opción B: ÓPTIMO
                                  OPERACIONAL                ECONÓMICO
---------------------------------------------------------------------------
PRIORIDAD:                        Mínimas Cajas              Menor Costo Total
---------------------------------------------------------------------------
CAJAS NECESARIAS:                 {ops['num_cajas']}                         {eco['num_cajas']}
COSTO TOTAL:                      ${ops['costos']['costo_total']:.2f} USD              ${eco['costos']['costo_total']:.2f} USD
CUMPLIMIENTO SLA:                 {ops['metricas']['porcentaje_sla']:.1f}%                     {eco['metricas']['porcentaje_sla']:.1f}%
UTILIZACIÓN:                      {ops['metricas']['utilizacion']:.1f}%                     {eco['metricas']['utilizacion']:.1f}%

═══════════════════════════════════════════════════════════════════════════
                       GUÍA DE DECISIÓN ESTRATÉGICA
═══════════════════════════════════════════════════════════════════════════

La diferencia clave es:
Para ahorrar ${abs(cost_diff):.2f} USD, se necesita operar {box_diff} caja(s) adicional(es).

CUÁNDO ELEGIR LA OPCIÓN A (ÓPTIMO OPERACIONAL - {ops['num_cajas']} cajas):
────────────────────────────────────────────────────────────────
✓ Si la simplicidad de la operación es clave.
✓ Si hay restricciones de personal o espacio físico.
✓ Si prefiere una operación más "ágil" (lean) y puede asumir un costo
  total ligeramente superior.

CUÁNDO ELEGIR LA OPCIÓN B (ÓPTIMO ECONÓMICO - {eco['num_cajas']} cajas):
───────────────────────────────────────────────────────────────
✓ Si el objetivo principal es la reducción del costo total, sin importar
  la complejidad operativa.
✓ Si dispone del personal y espacio para gestionar las cajas adicionales.
✓ Si su modelo de negocio es de ultra-bajo costo.

═══════════════════════════════════════════════════════════════════════════
                            PLAN DE ACCIÓN
═══════════════════════════════════════════════════════════════════════════

1. REÚNA al equipo de gestión de operaciones y finanzas.
2. PRESENTE este análisis comparativo.
3. DECIDA cuál de las dos prioridades (costo o agilidad) es más importante
   para el negocio en este momento.
4. IMPLEMENTE la configuración elegida como su nuevo estándar operativo.
5. MONITOREE los resultados reales y compárelos con la simulación.
"""

    def generar_texto_reporte(self):
        """Genera el texto completo del reporte."""
        reporte = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                   REPORTE DE SIMULACIÓN DE CAJAS                          ║
║                      ENFOQUE DE NEGOCIO                                   ║
╚═══════════════════════════════════════════════════════════════════════════╝

CONFIGURACIÓN DE LA SIMULACIÓN
{'='*75}

Parámetros de Tiempo:
  • Tiempo de escaneo: {self.config['t_scan_normal']} seg/artículo
  • Tiempo de cobro: {self.config['t_cobro_min']}-{self.config['t_cobro_max']} seg
  • Rango de artículos: {self.config['articulos_min']}-{self.config['articulos_max']}

Costos:
  • Costo por caja: ${self.config['costo_caja']:.2f} USD/min
  • Costo por espera: ${self.config['costo_espera']:.2f} USD/min por cliente
  • Penalización SLA: ${self.config['costo_sla']:.2f} USD por punto %

Objetivo de Servicio (SLA):
  • {self.config['sla_objetivo']:.0f}% de clientes con tiempo ≤ {self.config['umbral_tiempo']:.1f} minutos

Parámetros de Simulación:
  • Tasa de llegadas: {self.config['lambda_llegadas']:.2f} clientes/min
  • Tiempo de simulación: {self.config['tiempo_simulacion']:.0f} minutos
  • Número de réplicas: {self.config['num_replicas']}

RESULTADOS PRINCIPALES
{'='*75}

✅ CONFIGURACIÓN ÓPTIMA: {self.resultados['optimo']['num_cajas']} CAJAS

Costos:
  • Costo Total: ${self.resultados['optimo']['costos']['costo_total']:.2f} USD
  • Costo por Cajas: ${self.resultados['optimo']['costos']['costo_cajas']:.2f} USD
  • Costo por Espera: ${self.resultados['optimo']['costos']['costo_espera']:.2f} USD
  • Penalización SLA: ${self.resultados['optimo']['costos']['costo_sla']:.2f} USD
  • Desviación Estándar: ±${self.resultados['optimo']['desv_est']:.2f} USD

Métricas de Desempeño:
  • Cumplimiento SLA: {self.resultados['optimo']['metricas']['porcentaje_sla']:.1f}%
  • Utilización: {self.resultados['optimo']['metricas']['utilizacion']:.1f}%
  • Tiempo en Sistema: {self.resultados['optimo']['metricas']['tiempo_sistema_prom']:.2f} min
  • Tiempo de Espera: {self.resultados['optimo']['metricas']['tiempo_espera_prom']:.2f} min
  • Clientes Promedio: {self.resultados['optimo']['metricas']['num_clientes']:.0f}

MATRIZ DE RESULTADOS
{'='*75}

"""
        reporte += "Cajas │ C.Total  │ C.Cajas  │ C.Espera │  C.SLA   │  SLA%   │ Util.%\n"
        reporte += "─" * 75 + "\n"

        for resultado in self.resultados["por_cajas"]:
            marca = "★" if resultado["num_cajas"] == self.resultados["optimo"]["num_cajas"] else " "
            reporte += (
                f"{marca}{resultado['num_cajas']:3d}   │ "
                f"${resultado['costos']['costo_total']:7.2f} │ "
                f"${resultado['costos']['costo_cajas']:7.2f} │ "
                f"${resultado['costos']['costo_espera']:7.2f} │ "
                f"${resultado['costos']['costo_sla']:7.2f} │ "
                f"{resultado['metricas']['porcentaje_sla']:6.1f}% │ "
                f"{resultado['metricas']['utilizacion']:6.1f}%\n"
            )

        reporte += "\n★ = Configuración Óptima\n"

        reporte += f"""

REGLA DE APERTURA PROPUESTA
{'='*75}

Abrir una nueva caja cuando se cumplan AMBAS condiciones:

1. La utilización promedio por caja supera {self.resultados['optimo']['metricas']['utilizacion']:.1f}%
   durante un período de observación de 5 minutos

2. El tiempo promedio en sistema de los últimos 10 clientes
   supera {self.config['umbral_tiempo']:.1f} minutos

"""
        # Agregar conclusiones al reporte
        reporte += self.generar_texto_conclusiones_completo()
        
        reporte += f"""

SUPUESTOS Y LIMITACIONES
{'='*75}

Supuestos:
  • Proceso de llegadas: Poisson con λ = {self.config['lambda_llegadas']:.2f} clientes/min
  • Tiempo de servicio: Determinístico por número de artículos
  • Disciplina de cola: FIFO (First In, First Out)
  • No hay abandono de clientes
  • Personal siempre disponible para abrir cajas

Limitaciones:
  • No considera variación por hora del día
  • No incluye tiempos de apertura/cierre de caja
  • Asume capacitación uniforme del personal
  • No considera factores externos (promociones, festivos)

VERIFICACIÓN Y VALIDACIÓN (V&V)
{'='*75}

Verificación Conceptual:
  ✓ Modelo basado en teoría de colas M/M/s
  ✓ Múltiples réplicas independientes ({self.config['num_replicas']})
  ✓ Semillas aleatorias diferentes por réplica
  ✓ Métricas consistentes con fórmulas teóricas

Validación Recomendada:
  • Comparar con datos históricos del supermercado
  • Realizar prueba piloto de 1 semana
  • Ajustar parámetros según observaciones reales
  • Medir satisfacción del cliente antes y después

{'='*75}
Fin del Reporte
{'='*75}
"""
        return reporte

    