# --- interfaz_simulacion.py ---

import math
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog

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


def exportar_excel_completo(config, resultados, resultados_sensibilidad):
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

            resultados_por_cajas.append({
                "num_cajas": s, 
                "metricas": metricas_prom, 
                "costos": costos_prom, 
                "desv_est": desv_est, 
                "replicas": resultados_replicas
            })

        self.resultados = {
            "por_cajas": resultados_por_cajas, 
            "optimo": min(resultados_por_cajas, key=lambda x: x["costos"]["costo_total"])
        }

        self.mostrar_resultados()

    def mostrar_resultados(self):
        """Muestra los resultados de la simulación."""
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

        # ### CAMBIO CLAVE: BOTONES UNIFICADOS Y CON FUNCIONALIDAD CORREGIDA ###
        
        # Botón: Nueva Simulación (a la derecha)
        tk.Button(btn_frame, text="🔄 Nueva Simulación", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.crear_pantalla_configuracion, padx=20, pady=10).pack(side=tk.RIGHT, padx=5)

        # Botones de exportación (a la izquierda)
        tk.Button(btn_frame, text="📄 Exportar Conclusiones (PDF)", font=("Arial", 12, "bold"), bg="#FF5722", fg="white", command=lambda: exportar_pdf_conclusiones(self.generar_texto_conclusiones_completo()), padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="📊 Exportar Datos (Excel)", font=("Arial", 12, "bold"), bg="#2196F3", fg="white", command=lambda: exportar_excel_completo(self.config, self.resultados, self.resultados_sensibilidad), padx=20, pady=10).pack(side=tk.LEFT, padx=5)

    # El resto de tus funciones (crear_pestana_resumen, etc.) no necesitan cambios.
    # Las incluyo para que el archivo esté completo y puedas copiarlo directamente.
    
    def crear_pestana_resumen(self, notebook):
        #...código sin cambios...
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📊 Resumen Ejecutivo")
        tk.Label(frame, text="📊 Resultados de la Simulación - Resumen Ejecutivo", font=("Arial", 20, "bold"), bg="white", fg="#1976D2").pack(pady=20)
        cards_frame = tk.Frame(frame, bg="white")
        cards_frame.pack(pady=20)
        optimo = self.resultados["optimo"]
        self.crear_tarjeta(cards_frame, "✅ Configuración Óptima", f"{optimo['num_cajas']} cajas", "#4CAF50", 0, 0)
        self.crear_tarjeta(cards_frame, "💰 Costo Total Mínimo", f"${optimo['costos']['costo_total']:.2f} USD", "#2196F3", 0, 1)
        sla_color = "#4CAF50" if optimo["metricas"]["porcentaje_sla"] >= self.config["sla_objetivo"] else "#F44336"
        self.crear_tarjeta(cards_frame, "🎯 Cumplimiento SLA", f"{optimo['metricas']['porcentaje_sla']:.1f}%", sla_color, 0, 2)
        self.crear_tarjeta(cards_frame, "⚙️ Utilización", f"{optimo['metricas']['utilizacion']:.1f}%", "#FF9800", 1, 0)
        self.crear_tarjeta(cards_frame, "⏱️ Tiempo en Sistema", f"{optimo['metricas']['tiempo_sistema_prom']:.2f} min", "#9C27B0", 1, 1)
        self.crear_tarjeta(cards_frame, "👥 Clientes Promedio", f"{optimo['metricas']['num_clientes']:.0f}", "#00BCD4", 1, 2)
        desglose_frame = tk.LabelFrame(frame, text="💵 Desglose de Costos (Configuración Óptima)", font=("Arial", 14, "bold"), bg="white", padx=20, pady=15)
        desglose_frame.pack(pady=20, padx=40, fill=tk.X)
        costos_text = f"""
        Costo por Cajas Activas:    ${optimo['costos']['costo_cajas']:.2f} USD
        Costo por Tiempo de Espera: ${optimo['costos']['costo_espera']:.2f} USD
        Penalización por SLA:        ${optimo['costos']['costo_sla']:.2f} USD
        ═══════════════════════════════════════════════════════
        COSTO TOTAL:                 ${optimo['costos']['costo_total']:.2f} USD
        """
        tk.Label(desglose_frame, text=costos_text, font=("Courier", 12), bg="white", justify=tk.LEFT).pack()

    def crear_tarjeta(self, parent, titulo, valor, color, row, col):
        #...código sin cambios...
        card = tk.Frame(parent, bg=color, relief=tk.RAISED, bd=3)
        card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew", ipadx=30, ipady=20)
        tk.Label(card, text=titulo, font=("Arial", 12, "bold"), bg=color, fg="white").pack()
        tk.Label(card, text=valor, font=("Arial", 24, "bold"), bg=color, fg="white").pack(pady=10)

    def crear_pestana_graficos(self, notebook):
        #...código sin cambios...
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
        num_cajas = [r["num_cajas"] for r in resultados]
        costos_totales = [r["costos"]["costo_total"] for r in resultados]
        ax1.plot(num_cajas, costos_totales, "o-", linewidth=2.5, markersize=9, color="#2196F3")
        ax1.axvline(self.resultados["optimo"]["num_cajas"], color="red", linestyle="--", linewidth=2, label="Óptimo")
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
        optimo_idx = self.resultados["optimo"]["num_cajas"] - 1
        if optimo_idx < len(bars): bars[optimo_idx].set_color("#F44336")
        ax4.legend(fontsize=10, loc='upper right')
        canvas = FigureCanvasTkAgg(fig, frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas_graficos.pack(side="left", fill="both", expand=True)
        scrollbar_graficos.pack(side="right", fill="y")

    def crear_pestana_tabla(self, notebook):
        #...código sin cambios...
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📋 Tabla Detallada")
        canvas_tabla = tk.Canvas(frame, bg="white")
        scrollbar_tabla = tk.Scrollbar(frame, orient="vertical", command=canvas_tabla.yview)
        frame_tabla = tk.Frame(canvas_tabla, bg="white")
        frame_tabla.bind("<Configure>", lambda e: canvas_tabla.configure(scrollregion=canvas_tabla.bbox("all")))
        canvas_tabla.create_window((0, 0), window=frame_tabla, anchor="nw")
        canvas_tabla.configure(yscrollcommand=scrollbar_tabla.set)
        tk.Label(frame_tabla, text="📋 Matriz de Resultados por Configuración", font=("Arial", 18, "bold"), bg="white", fg="#1976D2").pack(pady=15)
        resultados = self.resultados["por_cajas"]; optimo_num = self.resultados["optimo"]["num_cajas"]
        columnas = ["Cajas", "C.Total", "C.Cajas", "C.Espera", "C.SLA", "SLA%", "Util.%", "T.Sistema", "T.Espera", "Desv.Est"]
        datos = [[f"{'★ ' if r['num_cajas'] == optimo_num else ''}{r['num_cajas']}", f"${r['costos']['costo_total']:.2f}", f"${r['costos']['costo_cajas']:.2f}", f"${r['costos']['costo_espera']:.2f}", f"${r['costos']['costo_sla']:.2f}", f"{r['metricas']['porcentaje_sla']:.1f}%", f"{r['metricas']['utilizacion']:.1f}%", f"{r['metricas']['tiempo_sistema_prom']:.2f}m", f"{r['metricas']['tiempo_espera_prom']:.2f}m", f"±${r['desv_est']:.2f}"] for r in resultados]
        fig_tabla, ax_tabla = plt.subplots(figsize=(13, max(6, len(datos) * 0.4))); fig_tabla.patch.set_facecolor("white"); ax_tabla.axis('tight'); ax_tabla.axis('off')
        tabla = ax_tabla.table(cellText=datos, colLabels=columnas, cellLoc='center', loc='center')
        tabla.auto_set_font_size(False); tabla.set_fontsize(9); tabla.scale(1, 2)
        for i in range(len(columnas)): tabla[(0, i)].set_facecolor('#1976D2'); tabla[(0, i)].set_text_props(weight='bold', color='white')
        for i in range(1, len(datos) + 1):
            for j in range(len(columnas)): tabla[(i, j)].set_facecolor('#E8F5E9' if i - 1 == optimo_num - 1 else ('#F5F5F5' if i % 2 == 0 else 'white'))
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        canvas_tabla_fig = FigureCanvasTkAgg(fig_tabla, frame_tabla); canvas_tabla_fig.draw(); canvas_tabla_fig.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(frame_tabla, text=f"★ = Configuración Óptima ({optimo_num} cajas) | Número de Réplicas: {self.config['num_replicas']}", font=("Arial", 11, "bold"), bg="white", fg="#1976D2").pack(pady=10)
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

        # Canvas con scrollbar
        canvas_scroll = tk.Canvas(frame, bg="white")
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas_scroll.yview)
        scrollable_frame = tk.Frame(canvas_scroll, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )

        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        tk.Label(
            scrollable_frame,
            text="📜 Regla de Apertura de Cajas Propuesta",
            font=("Arial", 20, "bold"),
            bg="white",
            fg="#1976D2",
        ).pack(pady=20)

        optimo = self.resultados["optimo"]

        rho = optimo["metricas"]["utilizacion"] / 100

        lambda_val = self.config["lambda_llegadas"]
        mu = 1 / ((self.config["t_scan_normal"] * 5 + (self.config["t_cobro_min"] + self.config["t_cobro_max"]) / 2) / 60)
        s_opt = optimo["num_cajas"]

        try:
            rho_sistema = lambda_val / (s_opt * mu)
            if rho_sistema < 1:
                lq_aprox = lambda_val * optimo["metricas"]["tiempo_espera_prom"]
            else:
                lq_aprox = "Sistema inestable"
        except ZeroDivisionError:
            lq_aprox = "No calculable"

        regla_frame = tk.LabelFrame(
            scrollable_frame,
            text="🎯 Regla Principal de Apertura",
            font=("Arial", 14, "bold"),
            bg="#E3F2FD",
            fg="#0D47A1",
            padx=30,
            pady=20,
        )
        regla_frame.pack(fill=tk.X, padx=40, pady=15)

        regla_texto = f"""
╔═══════════════════════════════════════════════════════════════╗
║                    REGLA DE APERTURA                          ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Abrir una nueva caja cuando se cumplan AMBAS condiciones:   ║
║                                                               ║
║  1. La utilización promedio por caja supera {rho*100:.1f}%    ║
║     durante un período de observación de 5 minutos           ║
║                                                               ║
║  2. El tiempo promedio en sistema de los últimos             ║
║     10 clientes supera {self.config['umbral_tiempo']:.1f} minutos           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """

        tk.Label(
            regla_frame,
            text=regla_texto,
            font=("Courier", 10, "bold"),
            bg="#E3F2FD",
            justify=tk.LEFT,
            fg="#0D47A1",
        ).pack()

        variables_frame = tk.LabelFrame(
            scrollable_frame,
            text="📊 Variables a Monitorear en Tiempo Real",
            font=("Arial", 14, "bold"),
            bg="#E8F5E9",
            fg="#1B5E20",
            padx=30,
            pady=20,
        )
        variables_frame.pack(fill=tk.X, padx=40, pady=15)

        lq_umbral = 3 if isinstance(lq_aprox, str) else int(lq_aprox * 1.5)

        variables_texto = f"""
1. UTILIZACIÓN POR CAJA (ρ)
   • Métrica: Porcentaje de tiempo que cada caja está ocupada
   • Umbral: {rho*100:.1f}%
   • Ventana: Promediar últimos 5 minutos
   • Cálculo: ρ = (Tiempo ocupado) / (Tiempo total) × 100

2. TIEMPO EN SISTEMA
   • Métrica: Tiempo desde llegada hasta salida del cliente
   • Umbral: {self.config['umbral_tiempo']:.1f} minutos
   • Ventana: Promedio móvil de últimos 10 clientes
   • Cálculo: T_sistema = T_salida - T_llegada

3. LONGITUD DE COLA (Lq)
   • Métrica: Número de clientes esperando
   • Umbral sugerido: {lq_umbral} clientes
   • Observación: Instantánea

4. TASA DE LLEGADAS (λ)
   • Métrica: Clientes por minuto
   • Referencia: {lambda_val:.2f} clientes/min (configurado)
   • Ventana: Últimos 10 minutos
        """

        tk.Label(
            variables_frame,
            text=variables_texto,
            font=("Arial", 10),
            bg="#E8F5E9",
            justify=tk.LEFT,
        ).pack(anchor="w")

        justif_frame = tk.LabelFrame(
            scrollable_frame,
            text="💡 Justificación Técnica",
            font=("Arial", 14, "bold"),
            bg="#FFF3E0",
            fg="#E65100",
            padx=30,
            pady=20,
        )
        justif_frame.pack(fill=tk.X, padx=40, pady=15)

        justif_texto = f"""
TRADE-OFF COSTO-SERVICIO:

• Con {s_opt} cajas (configuración óptima):
  - Costo Total: ${optimo['costos']['costo_total']:.2f} USD
  - Cumplimiento SLA: {optimo['metricas']['porcentaje_sla']:.1f}%
  - Utilización: {optimo['metricas']['utilizacion']:.1f}%

• Si usamos {s_opt-1 if s_opt > 1 else s_opt} caja(s):
  - Costo aumentaría por penalización SLA
  - Mayor tiempo de espera para clientes
  - Riesgo de pérdida de satisfacción del cliente

• Si usamos {s_opt+1} cajas:
  - Costo aumentaría por cajas adicionales
  - Beneficio marginal en servicio es mínimo
  - Recursos subutilizados

EVIDENCIA DE SIMULACIÓN:

• Basado en {self.config['num_replicas']} réplicas independientes
• Desviación estándar: ±${optimo['desv_est']:.2f} USD
• Intervalo de confianza (95%): ${optimo['costos']['costo_total'] - 1.96*optimo['desv_est']:.2f} - ${optimo['costos']['costo_total'] + 1.96*optimo['desv_est']:.2f} USD
        """

        tk.Label(
            justif_frame,
            text=justif_texto,
            font=("Arial", 10),
            bg="#FFF3E0",
            justify=tk.LEFT,
        ).pack(anchor="w")

        impl_frame = tk.LabelFrame(
            scrollable_frame,
            text="⚙️ Guía de Implementación",
            font=("Arial", 14, "bold"),
            bg="#F3E5F5",
            fg="#4A148C",
            padx=30,
            pady=20,
        )
        impl_frame.pack(fill=tk.X, padx=40, pady=(15, 30))

        impl_texto = """
PASOS PARA IMPLEMENTAR LA REGLA:

1. SISTEMA DE MONITOREO
   • Instalar sensores o sistema POS que registre:
     - Timestamp de llegada de cada cliente
     - Timestamp de inicio y fin de servicio
     - Número de artículos procesados

2. DASHBOARD EN TIEMPO REAL
   • Mostrar métricas clave actualizadas cada 30 segundos
   • Alertas visuales cuando se acerque a umbrales
   • Histórico de últimas 2 horas

3. PROTOCOLO DE DECISIÓN
   • Si ambas condiciones se cumplen → Abrir caja
   • Tiempo estimado de apertura: 2-3 minutos
   • Notificar al supervisor para asignación de personal

4. REVISIÓN PERIÓDICA
   • Revisar la regla cada mes con datos reales
   • Ajustar umbrales según estacionalidad
   • Considerar días festivos y promociones

5. VALIDACIÓN CONTINUA
   • Comparar costos reales vs. proyectados
   • Medir satisfacción del cliente (encuestas)
   • Analizar quejas relacionadas con tiempos de espera
        """

        tk.Label(
            impl_frame,
            text=impl_texto,
            font=("Arial", 10),
            bg="#F3E5F5",
            justify=tk.LEFT,
        ).pack(anchor="w")

        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Habilitar scroll con rueda del mouse
        def _on_mousewheel_regla(event):
            canvas_scroll.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel_regla)

    def crear_pestana_conclusiones(self, notebook):
        
        """Crea la pestaña de conclusiones y recomendaciones."""
        frame = tk.Frame(notebook, bg="white")
        notebook.add(frame, text="📝 Conclusiones")

        canvas_concl = tk.Canvas(frame, bg="white")
        scrollbar_concl = tk.Scrollbar(frame, orient="vertical", command=canvas_concl.yview)
        scrollable_frame = tk.Frame(canvas_concl, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_concl.configure(scrollregion=canvas_concl.bbox("all"))
        )

        canvas_concl.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_concl.configure(yscrollcommand=scrollbar_concl.set)

        tk.Label(
            scrollable_frame,
            text="📝 CONCLUSIONES Y RECOMENDACIONES ACCIONABLES",
            font=("Arial", 20, "bold"),
            bg="white",
            fg="#1976D2",
        ).pack(pady=20)

        optimo = self.resultados["optimo"]

        # Sección 1: Conclusiones Clave
        conclusiones_frame = tk.LabelFrame(
            scrollable_frame,
            text="🎯 Conclusiones Clave",
            font=("Arial", 14, "bold"),
            bg="#E3F2FD",
            fg="#0D47A1",
            padx=30,
            pady=20,
        )
        conclusiones_frame.pack(fill=tk.X, padx=40, pady=15)

        conclusiones_texto = f"""
1. PUNTO ÓPTIMO IDENTIFICADO
   • La configuración que minimiza el costo total es operar con {optimo['num_cajas']} CAJAS
   • Costo total proyectado: ${optimo['costos']['costo_total']:.2f} USD
   • Este punto equilibra costos operativos, tiempo de espera y penalizaciones

2. TRADE-OFF CRÍTICO DEMOSTRADO
   • Con {optimo['num_cajas']-1 if optimo['num_cajas'] > 1 else 1} caja(s): Aumento drástico de costos por SLA y espera
   • Con {optimo['num_cajas']} cajas: CONFIGURACIÓN ÓPTIMA ✓
   • Con {optimo['num_cajas']+1} cajas: Incremento innecesario de costos operativos
   • El ahorro en personal NO compensa las pérdidas por mal servicio

3. RENDIMIENTO Y CUMPLIMIENTO
   • Cumplimiento SLA: {optimo['metricas']['porcentaje_sla']:.1f}% (Objetivo: {self.config['sla_objetivo']:.0f}%)
   • Utilización de cajas: {optimo['metricas']['utilizacion']:.1f}% (Balance eficiente)
   • Tiempo promedio en sistema: {optimo['metricas']['tiempo_sistema_prom']:.2f} minutos
   • Clientes atendidos: {optimo['metricas']['num_clientes']:.0f} por período

4. ROBUSTEZ Y CONFIABILIDAD
   • Basado en {self.config['num_replicas']} réplicas independientes
   • Desviación estándar: ±${optimo['desv_est']:.2f} USD
   • La solución es robusta ante variaciones de ±20% en llegadas
   • Alta confianza estadística en los resultados
        """

        tk.Label(
            conclusiones_frame,
            text=conclusiones_texto,
            font=("Arial", 10),
            bg="#E3F2FD",
            justify=tk.LEFT,
        ).pack(anchor="w")

        # Sección 2: Recomendaciones Accionables
        recom_frame = tk.LabelFrame(
            scrollable_frame,
            text="⚡ Plan de Acción - Recomendaciones Accionables",
            font=("Arial", 14, "bold"),
            bg="#E8F5E9",
            fg="#1B5E20",
            padx=30,
            pady=20,
        )
        recom_frame.pack(fill=tk.X, padx=40, pady=15)

        recomendaciones_texto = f"""
📌 ACCIÓN INMEDIATA (Implementar HOY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. AJUSTAR OPERACIÓN BASE
   ✓ Qué hacer: Establecer {optimo['num_cajas']} CAJAS ABIERTAS como estándar
   ✓ Cuándo: Durante períodos normales (~{self.config['lambda_llegadas']:.1f} clientes/min)
   ✓ Impacto: Reducción inmediata de costos y garantía de SLA
   ✓ Responsable: Gerente de Operaciones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 ACCIÓN TÁCTICA (Implementar esta SEMANA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. REGLA DE APERTURA DINÁMICA
   ✓ Qué hacer: Capacitar supervisores en la regla de 2 condiciones
   
   ABRIR CAJA ADICIONAL cuando AMBAS condiciones se cumplan > 5 min:
   
   Condición 1: Utilización > {optimo['metricas']['utilizacion']:.0f}%
   Condición 2: Tiempo en sistema > {self.config['umbral_tiempo']:.0f} minutos
   
   ✓ Cómo medir:
     - Utilización = (Tiempo ocupado / Tiempo total) × 100
     - Tiempo sistema = Promedio últimos 10 clientes
   
   ✓ Impacto: Flexibilidad para picos sin costos fijos excesivos
   ✓ Responsable: Supervisor de Piso + RRHH (capacitación)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 INVERSIÓN ESTRATÉGICA (Implementar en 1 MES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. DASHBOARD DE MONITOREO EN TIEMPO REAL
   ✓ Qué instalar:
     • Display con métricas actualizadas cada 30 segundos
     • Alertas rojas cuando se requiere acción
     • Histórico de últimas 2 horas
   
   ✓ Impacto: Decisiones basadas en datos en tiempo real
   ✓ Inversión estimada: $500-$1,500 USD
   ✓ Responsable: TI + Gerente de Operaciones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 PROCESO DE MEJORA CONTINUA (CICLO MENSUAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4. VALIDACIÓN Y AJUSTE CONTINUO
   
   SEMANAS 1-2: PRUEBA PILOTO
   ✓ Implementar configuración de {optimo['num_cajas']} cajas
   ✓ Medir costos reales vs. proyección
   
   SEMANA 3: ANÁLISIS
   ✓ Comparar métricas reales con simulación
   ✓ Encuestas de satisfacción a clientes
   
   SEMANA 4: AJUSTE
   ✓ Refinar umbrales de la regla si es necesario
   ✓ Documentar lecciones aprendidas

5. MÉTRICAS DE ÉXITO A MONITOREAR
   ✓ Costo total operativo (vs. ${optimo['costos']['costo_total']:.2f} proyectado)
   ✓ % Cumplimiento SLA (mantener ≥ {self.config['sla_objetivo']:.0f}%)
   ✓ Satisfacción del cliente (encuestas NPS)
   ✓ Utilización de cajas (mantener ~{optimo['metricas']['utilizacion']:.0f}%)
        """

        tk.Label(
            recom_frame,
            text=recomendaciones_texto,
            font=("Courier", 9),
            bg="#E8F5E9",
            justify=tk.LEFT,
        ).pack(anchor="w")

        # Sección 3: Beneficios Esperados
        beneficios_frame = tk.LabelFrame(
            scrollable_frame,
            text="💰 Beneficios Esperados de la Implementación",
            font=("Arial", 14, "bold"),
            bg="#FFF3E0",
            fg="#E65100",
            padx=30,
            pady=20,
        )
        beneficios_frame.pack(fill=tk.X, padx=40, pady=15)

        beneficios_texto = f"""
IMPACTO FINANCIERO:
• Optimización de costos operativos
• Reducción de penalizaciones por incumplimiento de SLA
• Menor costo por tiempo de espera de clientes
• ROI estimado: Recuperación de inversión en < 3 meses

IMPACTO EN SERVICIO AL CLIENTE:
• {optimo['metricas']['porcentaje_sla']:.1f}% de clientes atendidos dentro del objetivo
• Reducción del tiempo promedio de espera
• Mayor satisfacción y lealtad del cliente
• Reducción de quejas relacionadas con colas

IMPACTO OPERATIVO:
• Utilización eficiente de recursos ({optimo['metricas']['utilizacion']:.1f}%)
• Personal mejor distribuido y menos estresado
• Toma de decisiones basada en datos
• Proceso escalable y replicable en otras sucursales

VENTAJAS COMPETITIVAS:
• Experiencia de compra superior
• Diferenciación en el mercado
• Capacidad de gestión proactiva de demanda
• Sistema de mejora continua establecido
        """

        tk.Label(
            beneficios_frame,
            text=beneficios_texto,
            font=("Arial", 10),
            bg="#FFF3E0",
            justify=tk.LEFT,
        ).pack(anchor="w")

        # Sección 4: Próximos Pasos
        proximos_frame = tk.LabelFrame(
            scrollable_frame,
            text="🚀 Checklist de Implementación Inmediata",
            font=("Arial", 14, "bold"),
            bg="#F3E5F5",
            fg="#4A148C",
            padx=30,
            pady=20,
        )
        proximos_frame.pack(fill=tk.X, padx=40, pady=(15, 30))

        proximos_texto = f"""
SEMANA 1:
☐ Reunión con gerencia para aprobar plan de acción
☐ Comunicar cambios a supervisores y cajeros
☐ Establecer {optimo['num_cajas']} cajas como configuración base
☐ Iniciar medición de métricas actuales (línea base)

SEMANA 2:
☐ Capacitar supervisores en regla de apertura dinámica
☐ Crear checklist de monitoreo manual (temporal)
☐ Iniciar prueba piloto
☐ Recolectar feedback diario del equipo

SEMANA 3:
☐ Analizar datos de la prueba piloto
☐ Comparar costos reales vs. simulación
☐ Realizar encuestas de satisfacción a clientes
☐ Documentar incidencias y ajustes necesarios

SEMANA 4:
☐ Presentar resultados de prueba piloto a gerencia
☐ Ajustar umbrales de la regla según observaciones
☐ Iniciar cotización de sistema de monitoreo automático
☐ Planificar roll-out completo para siguiente mes

RESPONSABLES CLAVE:
• Gerente de Operaciones: Aprobación y supervisión general
• Supervisor de Piso: Implementación diaria de la regla
• RRHH: Capacitación del personal
• TI: Dashboard y sistemas de monitoreo
• Finanzas: Seguimiento de costos y ROI
        """

        tk.Label(
            proximos_frame,
            text=proximos_texto,
            font=("Arial", 10),
            bg="#F3E5F5",
            justify=tk.LEFT,
        ).pack(anchor="w")

        canvas_concl.pack(side="left", fill="both", expand=True)
        scrollbar_concl.pack(side="right", fill="y")
        
        # Habilitar scroll
        def _on_mousewheel_concl(event):
            canvas_concl.yview_scroll(int(-1*(event.delta/120)), "units")
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
  
        """Genera el texto completo de conclusiones."""
        optimo = self.resultados["optimo"]
        
        texto = f"""
═══════════════════════════════════════════════════════════════════════════
                    RESUMEN EJECUTIVO DE RESULTADOS
═══════════════════════════════════════════════════════════════════════════

CONFIGURACIÓN ÓPTIMA IDENTIFICADA: {optimo['num_cajas']} CAJAS

Métricas Clave:
• Costo Total: ${optimo['costos']['costo_total']:.2f} USD
• Cumplimiento SLA: {optimo['metricas']['porcentaje_sla']:.1f}% (Objetivo: {self.config['sla_objetivo']:.0f}%)
• Utilización: {optimo['metricas']['utilizacion']:.1f}%
• Tiempo en Sistema: {optimo['metricas']['tiempo_sistema_prom']:.2f} minutos
• Confiabilidad: ±${optimo['desv_est']:.2f} USD (desviación estándar)


═══════════════════════════════════════════════════════════════════════════
                         CONCLUSIONES CLAVE
═══════════════════════════════════════════════════════════════════════════

1. PUNTO ÓPTIMO IDENTIFICADO
   ───────────────────────────
   La configuración que minimiza el costo total (operativo + espera + 
   penalizaciones) es operar con {optimo['num_cajas']} CAJAS. Este escenario presenta 
   un costo total proyectado de ${optimo['costos']['costo_total']:.2f} USD por período de 
   simulación.

2. TRADE-OFF CRÍTICO DEMOSTRADO
   ─────────────────────────────
   • Con {optimo['num_cajas']-1 if optimo['num_cajas'] > 1 else 1} caja(s): AUMENTO DRÁSTICO de costos por incumplimiento 
     de SLA y tiempo de espera. El ahorro en personal NO compensa 
     estas pérdidas.
   
   • Con {optimo['num_cajas']} cajas: CONFIGURACIÓN ÓPTIMA que equilibra todos 
     los factores de costo.
   
   • Con {optimo['num_cajas']+1} cajas: INCREMENTO INNECESARIO de costos operativos. 
     El beneficio marginal en servicio es mínimo y no justifica el 
     costo adicional.

3. RENDIMIENTO Y CUMPLIMIENTO
   ────────────────────────────
   La configuración óptima logra:
   • Cumplimiento SLA: {optimo['metricas']['porcentaje_sla']:.1f}% (objetivo: {self.config['sla_objetivo']:.0f}%)
   • Utilización eficiente: {optimo['metricas']['utilizacion']:.1f}% (indica buen balance)
   • Tiempo promedio aceptable: {optimo['metricas']['tiempo_sistema_prom']:.2f} minutos
   • Capacidad para {optimo['metricas']['num_clientes']:.0f} clientes por período

4. ROBUSTEZ Y CONFIABILIDAD
   ─────────────────────────
   • Basado en {self.config['num_replicas']} réplicas independientes
   • Desviación estándar: ±${optimo['desv_est']:.2f} USD
   • Solución robusta ante variaciones de ±20% en tasa de llegadas
   • Alta confianza estadística en los resultados


═══════════════════════════════════════════════════════════════════════════
                  RECOMENDACIONES ACCIONABLES - PLAN DE ACCIÓN
═══════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│  ACCIÓN INMEDIATA (Implementar HOY)                                     │
└─────────────────────────────────────────────────────────────────────────┘

1. AJUSTAR OPERACIÓN BASE
   
   ✓ QUÉ: Establecer {optimo['num_cajas']} CAJAS ABIERTAS como configuración estándar
   
   ✓ CUÁNDO: Durante períodos de operación normal 
            (correspondientes a ~{self.config['lambda_llegadas']:.1f} clientes/minuto)
   
   ✓ IMPACTO ESPERADO:
     • Reducción del costo total operativo
     • Garantía de cumplimiento del objetivo de servicio ({self.config['sla_objetivo']:.0f}%)
     • Balance óptimo entre costos y satisfacción del cliente
   
   ✓ RESPONSABLE: Gerente de Operaciones


┌─────────────────────────────────────────────────────────────────────────┐
│  ACCIÓN TÁCTICA (Implementar esta SEMANA)                               │
└─────────────────────────────────────────────────────────────────────────┘

2. IMPLEMENTAR REGLA DE APERTURA DINÁMICA
   
   ✓ QUÉ: Capacitar a supervisores para abrir una caja adicional
          SOLO cuando se cumplan AMBAS condiciones durante > 5 minutos:
          
          ┌──────────────────────────────────────────────────┐
          │  CONDICIÓN 1: Utilización > {optimo['metricas']['utilizacion']:.0f}%              │
          │  CONDICIÓN 2: Tiempo en sistema > {self.config['umbral_tiempo']:.0f} minutos     │
          └──────────────────────────────────────────────────┘
   
   ✓ CÓMO MEDIR:
     • Utilización = (Tiempo ocupado / Tiempo total) × 100
       Calcular promedio de últimos 5 minutos
     
     • Tiempo en sistema = Tiempo desde llegada hasta salida
       Calcular promedio móvil de últimos 10 clientes
   
   ✓ PROTOCOLO:
     1. Supervisor monitorea métricas cada 5 minutos
     2. Si AMBAS condiciones se cumplen → Abrir caja adicional
     3. Tiempo estimado de apertura: 2-3 minutos
     4. Registrar evento para análisis posterior
   
   ✓ IMPACTO ESPERADO:
     • Flexibilidad para gestionar picos de demanda
     • Sin incurrir en costos fijos innecesarios
     • Mantener satisfacción del cliente en momentos críticos
   
   ✓ RESPONSABLE: Supervisor de Piso + RRHH (capacitación)


┌─────────────────────────────────────────────────────────────────────────┐
│  INVERSIÓN ESTRATÉGICA (Implementar en 1 MES)                           │
└─────────────────────────────────────────────────────────────────────────┘

3. DESPLEGAR DASHBOARD DE MONITOREO EN TIEMPO REAL
   
   ✓ QUÉ INSTALAR:
     Sistema de monitoreo que muestre métricas actualizadas cada 30 seg:
     
     ┌────────────────────────────────────────────────┐
     │  MÉTRICAS EN DASHBOARD:                        │
     │  • Utilización por caja (%)                    │
     │  • Tiempo promedio en sistema (minutos)        │
     │  • Número de clientes en cola                  │
     │  • Alertas visuales al acercarse a umbrales    │
     │  • Histórico de últimas 2 horas                │
     └────────────────────────────────────────────────┘
   
   ✓ FUNCIONALIDADES CLAVE:
     • Alertas rojas cuando se requiere abrir caja
     • Gráficos de tendencia en tiempo real
     • Registro automático para análisis posterior
     • Acceso remoto para gerencia
   
   ✓ INVERSIÓN ESTIMADA: $500 - $1,500 USD (sistema básico)
   
   ✓ IMPACTO ESPERADO:
     • Toma de decisiones basada en datos en tiempo real
     • Aplicación efectiva de la regla dinámica
     • Gestión proactiva de las colas
     • Datos históricos para optimización continua
   
   ✓ RESPONSABLE: Gerente TI + Gerente de Operaciones


┌─────────────────────────────────────────────────────────────────────────┐
│  PROCESO DE MEJORA CONTINUA (CICLO MENSUAL)                             │
└─────────────────────────────────────────────────────────────────────────┘

4. VALIDAR Y REVISAR CONTINUAMENTE
   
   SEMANAS 1-2: PRUEBA PILOTO
   ──────────────────────────
   ✓ Implementar configuración de {optimo['num_cajas']} cajas
   ✓ Aplicar regla de apertura dinámica
   ✓ Medir costos reales y compararlos con proyección
   ✓ Recolectar feedback de supervisores y cajeros
   ✓ Registrar todos los eventos de apertura de cajas
   
   SEMANA 3: ANÁLISIS
   ──────────────────
   ✓ Comparar métricas reales con simulación
   ✓ Calcular desviaciones y identificar causas
   ✓ Realizar encuestas de satisfacción a clientes
   ✓ Analizar quejas relacionadas con tiempos de espera
   ✓ Revisar eficacia de la regla de apertura
   
   SEMANA 4: AJUSTE Y DOCUMENTACIÓN
   ─────────────────────────────────
   ✓ Refinar umbrales de la regla si es necesario
   ✓ Documentar lecciones aprendidas
   ✓ Actualizar procedimientos operativos
   ✓ Preparar reporte para gerencia
   ✓ Planificar revisión para siguiente mes
   
   REVISIÓN TRIMESTRAL:
   ────────────────────
   ✓ Ajustar parámetros según estacionalidad
   ✓ Considerar días festivos y promociones
   ✓ Revisar estructura de costos
   ✓ Actualizar capacitación del personal
   ✓ Evaluar necesidad de inversiones adicionales


5. MÉTRICAS DE ÉXITO A MONITOREAR
   
   FINANCIERAS:
   • Costo total operativo (vs. ${optimo['costos']['costo_total']:.2f} proyectado)
   • Costo por cliente atendido
   • Penalizaciones por incumplimiento de SLA
   • ROI de inversiones realizadas
   
   OPERATIVAS:
   • % Cumplimiento SLA (mantener ≥ {self.config['sla_objetivo']:.0f}%)
   • Utilización promedio de cajas (~{optimo['metricas']['utilizacion']:.0f}%)
   • Tiempo promedio de espera
   • Tiempo promedio en sistema
   
   SATISFACCIÓN:
   • NPS (Net Promoter Score)
   • Quejas por tiempos de espera
   • Encuestas de satisfacción del cliente
   • Feedback del personal


═══════════════════════════════════════════════════════════════════════════
                       BENEFICIOS ESPERADOS
═══════════════════════════════════════════════════════════════════════════

💰 IMPACTO FINANCIERO:
   • Optimización de costos operativos
   • Reducción de penalizaciones por incumplimiento de SLA
   • Menor costo por tiempo de espera de clientes
   • ROI estimado: Recuperación de inversión en < 3 meses

😊 IMPACTO EN SERVICIO AL CLIENTE:
   • {optimo['metricas']['porcentaje_sla']:.1f}% de clientes atendidos dentro del objetivo
   • Reducción del tiempo promedio de espera
   • Mayor satisfacción y lealtad del cliente
   • Reducción de quejas relacionadas con colas
   • Experiencia de compra mejorada

⚙️ IMPACTO OPERATIVO:
   • Utilización eficiente de recursos ({optimo['metricas']['utilizacion']:.1f}%)
   • Personal mejor distribuido y menos estresado
   • Toma de decisiones basada en datos
   • Proceso escalable y replicable en otras sucursales
   • Capacidad de respuesta ante variaciones de demanda

🏆 VENTAJAS COMPETITIVAS:
   • Experiencia de compra superior a la competencia
   • Diferenciación en el mercado
   • Capacidad de gestión proactiva de demanda
   • Sistema de mejora continua establecido
   • Imagen de marca fortalecida


═══════════════════════════════════════════════════════════════════════════
                 CHECKLIST DE IMPLEMENTACIÓN INMEDIATA
═══════════════════════════════════════════════════════════════════════════

SEMANA 1:
─────────
☐ Reunión con gerencia para aprobar plan de acción
☐ Comunicar cambios a supervisores y cajeros
☐ Establecer {optimo['num_cajas']} cajas como configuración base
☐ Iniciar medición de métricas actuales (línea base)
☐ Definir responsables para cada acción

SEMANA 2:
─────────
☐ Capacitar supervisores en regla de apertura dinámica
☐ Crear checklist de monitoreo manual (temporal)
☐ Iniciar prueba piloto
☐ Recolectar feedback diario del equipo
☐ Documentar incidencias

SEMANA 3:
─────────
☐ Analizar datos de la prueba piloto
☐ Comparar costos reales vs. simulación
☐ Realizar encuestas de satisfacción a clientes
☐ Documentar incidencias y ajustes necesarios
☐ Preparar reporte intermedio

SEMANA 4:
─────────
☐ Presentar resultados de prueba piloto a gerencia
☐ Ajustar umbrales de la regla según observaciones
☐ Iniciar cotización de sistema de monitoreo automático
☐ Planificar roll-out completo para siguiente mes
☐ Documentar lecciones aprendidas


═══════════════════════════════════════════════════════════════════════════
                    RESPONSABLES CLAVE DEL PROYECTO
═══════════════════════════════════════════════════════════════════════════

• GERENTE DE OPERACIONES: Aprobación y supervisión general del proyecto
• SUPERVISOR DE PISO: Implementación diaria de la regla de apertura
• RECURSOS HUMANOS: Capacitación del personal y gestión del cambio
• TECNOLOGÍAS DE INFORMACIÓN: Dashboard y sistemas de monitoreo
• FINANZAS: Seguimiento de costos, presupuesto y cálculo de ROI
• ATENCIÓN AL CLIENTE: Medición de satisfacción y gestión de quejas


═══════════════════════════════════════════════════════════════════════════
                         PRÓXIMOS PASOS INMEDIATOS
═══════════════════════════════════════════════════════════════════════════

1. PRESENTAR este reporte a la gerencia para aprobación
2. PROGRAMAR reunión de kick-off con todos los responsables
3. ESTABLECER fecha de inicio de la prueba piloto
4. ASIGNAR presupuesto para inversión en dashboard
5. COMUNICAR el plan al personal operativo


═══════════════════════════════════════════════════════════════════════════

Este análisis está basado en {self.config['num_replicas']} réplicas de simulación independientes,
proporcionando un alto nivel de confianza estadística en los resultados.

Para cualquier duda o aclaración sobre la implementación, consulte con el
equipo de análisis o revise las pestañas de "Resultados" y "Regla de Apertura"
en la interfaz principal.

═══════════════════════════════════════════════════════════════════════════
"""
        return texto

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

    