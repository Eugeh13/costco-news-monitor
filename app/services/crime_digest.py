"""
Crime digest — resumen mensual de incidencia delictiva oficial por municipio.

Toma las filas municipales del SESNSP (vía SESNSPMunicipalData) y produce un
digest comparativo (mes vs mes anterior, vs mismo mes del año pasado, y
acumulado anual) para los municipios donde hay tiendas Costco.

Es un módulo SEPARADO del pipeline de alertas en tiempo real: contexto
estratégico mensual, no detección de incidentes.
"""

from __future__ import annotations

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# Municipios con Costco monitoreado (clave INEGI 5 dígitos → nombre)
MUNICIPIOS_COSTCO: dict[str, str] = {
    "19039": "Monterrey",                 # Costco Carretera Nacional
    "19019": "San Pedro Garza García",    # Costco Valle Oriente
}

# Delitos relevantes para la operación de una tienda (nombre → filtro de fila)
GRUPOS_DELITO = [
    ("Robo de vehículo", lambda r: r.get("Subtipo de delito") == "Robo de vehículo automotor"),
    ("Robo a negocio", lambda r: r.get("Subtipo de delito") == "Robo a negocio"),
    ("Homicidio doloso", lambda r: r.get("Subtipo de delito") == "Homicidio doloso"),
    ("Extorsión", lambda r: r.get("Tipo de delito") == "Extorsión"),
]


class CrimeDigestService:
    """Calcula y formatea el digest mensual de criminalidad por municipio."""

    def __init__(self, municipios: dict[str, str] | None = None) -> None:
        self._municipios = municipios or MUNICIPIOS_COSTCO

    def build(self, rows: list[dict]) -> str:
        """Construye el texto del digest a partir de las filas del SESNSP."""
        if not rows:
            return "⚠️ Sin datos del SESNSP para generar el digest."

        anio_col = self._year_column(rows[0])
        year, month_idx = self._latest_period(rows, anio_col)

        lines = [
            f"📊 *Contexto delictivo — {MESES[month_idx]} {year}*",
            "_Cifras oficiales SESNSP (carpetas de investigación)_",
        ]

        for clave, nombre in self._municipios.items():
            m_rows = [r for r in rows if r.get("Cve. Municipio") == clave]
            if not m_rows:
                continue

            lines.append(f"\n📍 *{nombre}*")
            for grupo, pred in GRUPOS_DELITO:
                g_rows = [r for r in m_rows if pred(r)]
                actual = self._month_total(g_rows, anio_col, year, month_idx)

                # Mes anterior (enero → diciembre del año previo)
                if month_idx > 0:
                    prev = self._month_total(g_rows, anio_col, year, month_idx - 1)
                else:
                    prev = self._month_total(g_rows, anio_col, year - 1, 11)

                # Mismo mes del año pasado
                yoy = self._month_total(g_rows, anio_col, year - 1, month_idx)

                lines.append(
                    f"  • {grupo}: *{actual}* "
                    f"({self._cmp(actual, prev, 'mes ant.')}, {self._cmp(actual, yoy, 'año ant.')})"
                )

            # Acumulado del año vs mismo periodo del año anterior (todos los grupos)
            acum = self._ytd_total(m_rows, anio_col, year, month_idx)
            acum_prev = self._ytd_total(m_rows, anio_col, year - 1, month_idx)
            lines.append(f"  Σ Acumulado {year} (delitos clave): *{acum}* vs {acum_prev} en {year - 1}")

        lines.append(f"\n🔗 Fuente: SESNSP, incidencia municipal (corte {MESES[month_idx]} {year})")
        return "\n".join(lines)

    # ── Private ──────────────────────────────────────────────

    @staticmethod
    def _year_column(row: dict) -> str:
        """El header puede venir como 'Año' (utf-8) o mal decodificado — detectarlo."""
        for col in row:
            if col.strip().lower().endswith("o") and "a" in col.strip().lower()[:2]:
                return col
        return list(row.keys())[0]

    def _latest_period(self, rows: list[dict], anio_col: str) -> tuple[int, int]:
        """Último (año, índice de mes) con datos reportados (celda no vacía)."""
        years = sorted({int(r[anio_col]) for r in rows if r.get(anio_col, "").isdigit()})
        for year in reversed(years):
            y_rows = [r for r in rows if r[anio_col] == str(year)]
            for idx in range(11, -1, -1):
                if any((r.get(MESES[idx]) or "").strip() != "" for r in y_rows):
                    return year, idx
        return years[-1] if years else 0, 0

    @staticmethod
    def _month_total(rows: list[dict], anio_col: str, year: int, month_idx: int) -> int:
        total = 0
        for r in rows:
            if r.get(anio_col) == str(year):
                val = (r.get(MESES[month_idx]) or "").strip()
                if val:
                    try:
                        total += int(float(val))
                    except ValueError:
                        pass
        return total

    def _ytd_total(self, m_rows: list[dict], anio_col: str, year: int, month_idx: int) -> int:
        """Suma de los grupos clave de enero al mes de corte."""
        total = 0
        for grupo, pred in GRUPOS_DELITO:
            g_rows = [r for r in m_rows if pred(r)]
            for idx in range(month_idx + 1):
                total += self._month_total(g_rows, anio_col, year, idx)
        return total

    @staticmethod
    def _cmp(actual: int, referencia: int, etiqueta: str) -> str:
        """'12 vs 15 mes ant. ↓20%' — con manejo de división entre cero."""
        if referencia == 0:
            delta = f"+{actual}" if actual > 0 else "="
        else:
            pct = round((actual - referencia) / referencia * 100)
            delta = "=" if pct == 0 else (f"↑{pct}%" if pct > 0 else f"↓{abs(pct)}%")
        return f"{etiqueta} {referencia} {delta}"
