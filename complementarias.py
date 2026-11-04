import sys
import csv
import calendar
from datetime import datetime
from collections import defaultdict

# ---------- AJUSTES ----------
HORAS_SEMANA = 15
PRECIO_HORA = 8.15
LIMITE_PACTADAS = 0.30   # 30% de las horas contratadas (60% si tu convenio lo amplía)
ARCHIVO_TURNOS = "horas.txt"
# -----------------------------

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def duracion(inicio, fin, descanso_min=0):
    f = "%H:%M"
    h = (datetime.strptime(fin, f) - datetime.strptime(inicio, f)).total_seconds() / 3600
    if h < 0:
        h += 24  # turno que cruza medianoche
    return h - descanso_min / 60


def leer_turnos(archivo, anio, mes):
    turnos = []
    with open(archivo, encoding="utf-8") as f:
        for n, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            p = linea.split()
            try:
                fecha = datetime.strptime(p[0], "%Y-%m-%d")
                desc = int(p[3]) if len(p) > 3 else 0
                h = duracion(p[1], p[2], desc)
            except (ValueError, IndexError):
                print(f"⚠ Línea {n} ignorada (formato incorrecto): {linea}")
                continue
            if (fecha.year, fecha.month) == (anio, mes):
                turnos.append((fecha, p[1], p[2], desc, h))
    turnos.sort(key=lambda t: (t[0], t[1]))
    return turnos


def tabla(cabecera, filas, alineacion=None):
    """Imprime una tabla de texto alineada."""
    filas = [[str(c) for c in fila] for fila in filas]
    anchos = [max(len(str(cabecera[i])), *(len(f[i]) for f in filas)) if filas
              else len(str(cabecera[i])) for i in range(len(cabecera))]
    alineacion = alineacion or ["<"] * len(cabecera)

    def fmt(fila):
        return " | ".join(f"{c:{a}{w}}" for c, a, w in zip(fila, alineacion, anchos))

    print(fmt(cabecera))
    print("-+-".join("-" * w for w in anchos))
    for f in filas:
        print(fmt(f))


def main(mes_txt, archivo=ARCHIVO_TURNOS):
    anio, mes = map(int, mes_txt.split("-"))
    turnos = leer_turnos(archivo, anio, mes)

    if not turnos:
        print(f"No hay turnos en {mes_txt} dentro de {archivo}")
        return

    # ---- Cálculos ----
    total = sum(t[4] for t in turnos)
    por_semana = defaultdict(float)
    for fecha, _, _, _, h in turnos:
        por_semana[fecha.isocalendar()[1]] += h

    dias_mes = calendar.monthrange(anio, mes)[1]
    contrato_mes = HORAS_SEMANA * dias_mes / 7
    compl = max(0, total - contrato_mes)
    importe = compl * PRECIO_HORA
    tope = contrato_mes * LIMITE_PACTADAS

    # ---- Tabla 1: detalle de turnos ----
    print(f"\n=== TURNOS DE {mes_txt} ===")
    filas = []
    for fecha, ini, fin, desc, h in turnos:
        filas.append([fecha.strftime("%d/%m/%Y"), DIAS[fecha.weekday()], ini, fin,
                      f"{desc} min" if desc else "-", f"{h:.2f}",
                      fecha.isocalendar()[1]])
    filas.append(["TOTAL", "", "", "", "", f"{total:.2f}", ""])
    tabla(["Fecha", "Día", "Inicio", "Fin", "Descanso", "Horas", "Sem."],
          filas, ["<", "<", ">", ">", ">", ">", ">"])

    # ---- Tabla 2: resumen por semana ----
    print("\n=== RESUMEN POR SEMANA (ISO) ===")
    filas_sem = []
    for s, h in sorted(por_semana.items()):
        filas_sem.append([s, f"{h:.2f}", f"{HORAS_SEMANA:.2f}", f"{h - HORAS_SEMANA:+.2f}"])
    tabla(["Semana", "Trabajadas", "Contrato", "Diferencia"], filas_sem, [">"] * 4)
    print("(Las semanas partidas entre dos meses solo cuentan los días de este mes.)")

    # ---- Tabla 3: resumen del mes ----
    print("\n=== RESUMEN DEL MES ===")
    resumen = [
        ["Horas trabajadas", f"{total:.2f} h"],
        ["Horas de contrato (mes)", f"{contrato_mes:.2f} h"],
        ["Horas complementarias", f"{compl:.2f} h"],
        ["Precio por hora", f"{PRECIO_HORA:.2f} €"],
        ["Importe bruto estimado", f"{importe:.2f} €"],
    ]
    tabla(["Concepto", "Valor"], resumen, ["<", ">"])
    if compl > tope:
        print(f"\n⚠ Superas el 30% de las horas contratadas ({tope:.2f} h): "
              "revisa si son pactadas/voluntarias.")

    # ---- Exportar a CSV (se abre bien en Excel) ----
    salida = f"resumen_{mes_txt}.csv"
    with open(salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Fecha", "Día", "Inicio", "Fin", "Descanso (min)", "Horas", "Semana"])
        for fecha, ini, fin, desc, h in turnos:
            w.writerow([fecha.strftime("%d/%m/%Y"), DIAS[fecha.weekday()], ini, fin, desc,
                        f"{h:.2f}".replace(".", ","), fecha.isocalendar()[1]])
        w.writerow([])
        w.writerow(["Horas trabajadas", f"{total:.2f}".replace(".", ",")])
        w.writerow(["Horas contrato mes", f"{contrato_mes:.2f}".replace(".", ",")])
        w.writerow(["Horas complementarias", f"{compl:.2f}".replace(".", ",")])
        w.writerow(["Importe bruto (€)", f"{importe:.2f}".replace(".", ",")])
    print(f"\nTabla guardada en: {salida}")


if __name__ == "__main__":
    mes_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m")
    main(mes_arg)