"""
SESNSP municipal data — descarga la incidencia delictiva municipal oficial.

Fuente: "Incidencia Delictiva del Fuero Común, Nueva Metodología" (IDM_NM),
nivel municipal, actualizada mensualmente (~día 20) por el SESNSP.

El archivo completo pesa ~380MB, así que se filtra EN STREAMING: nunca se
carga entero a memoria ni a disco. La URL vigente se descubre desde la página
del dataset en datos.gob.mx (el nombre del archivo cambia cada mes:
IDM_NM_dic25.csv, IDM_NM_ene26.csv, ...).
"""

from __future__ import annotations

import csv
import re
from datetime import date
from typing import Optional

import requests

DATASET_PAGE = "https://www.datos.gob.mx/dataset/incidencia_delictiva"

# Abreviaturas de mes que usa el SESNSP en el nombre del archivo
# (IDM_NM_dic25.csv, IDM_NM_ene26.csv, ...). Índice 0 = enero.
_MESES_ABREV = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class SESNSPMunicipalData:
    """Descarga y filtra el CSV municipal del SESNSP por claves de municipio."""

    def discover_url(self) -> Optional[str]:
        """Encuentra la URL vigente del CSV municipal (IDM_NM_*.csv) en datos.gob.mx."""
        try:
            response = self._get_dataset_page()
        except Exception as e:
            print(f"  ⚠️ SESNSP: no se pudo leer la página del dataset — {e}")
            return None

        # El archivo municipal es IDM_NM_<mes><año>.csv (estatal es INM_, víctimas IDVFC_)
        match = re.search(r'https://[^"\']*IDM_NM[^"\']*\.csv', response.text)
        if not match:
            print("  ⚠️ SESNSP: no se encontró el enlace IDM_NM_*.csv en el dataset")
            return None
        return match.group(0)

    def probe_beyond(self, url_actual: str, hoy: Optional[date] = None) -> str:
        """
        Sondea cortes POSTERIORES al descubierto y devuelve el más reciente.

        datos.gob.mx lista el corte con meses de rezago (verificado 2026-06:
        solo aparece dic25). Como el nombre del archivo es predecible
        (IDM_NM_<mes><año2>.csv) y vive en repodatos.atdt.gob.mx, se prueba
        con HEAD cada mes siguiente hasta el mes actual y se usa la última
        URL que responda 200. Si ninguna existe, se conserva la descubierta.

        `hoy` es inyectable solo para tests (default: fecha real).
        """
        hoy = hoy or date.today()
        match = re.search(r"IDM_NM_([a-z]{3})(\d{2})\.csv", url_actual, re.IGNORECASE)
        if not match or match.group(1).lower() not in _MESES_ABREV:
            return url_actual

        nombre_actual = match.group(0)
        anio = 2000 + int(match.group(2))
        mes = _MESES_ABREV.index(match.group(1).lower()) + 1
        mejor_url, mejor_anio, mejor_mes = url_actual, anio, mes

        while (anio, mes) < (hoy.year, hoy.month):
            mes += 1
            if mes > 12:
                anio, mes = anio + 1, 1
            candidato = url_actual.replace(
                nombre_actual, f"IDM_NM_{_MESES_ABREV[mes - 1]}{anio % 100:02d}.csv"
            )
            try:
                # El CSV vive en repodatos.atdt.gob.mx, cuyo SSL sí valida
                # completo (el fallback sin verify es solo del descubrimiento).
                response = requests.head(
                    candidato,
                    headers={"User-Agent": _BROWSER_UA},
                    timeout=15,
                    allow_redirects=True,
                )
                if response.status_code == 200:
                    mejor_url, mejor_anio, mejor_mes = candidato, anio, mes
            except requests.RequestException:
                pass  # error transitorio: seguir probando los meses restantes

        if mejor_url != url_actual:
            print(f"  ✓ SESNSP: corte más nuevo disponible — {mejor_url.rsplit('/', 1)[-1]}")

        rezago = (hoy.year - mejor_anio) * 12 + (hoy.month - mejor_mes)
        if rezago > 2:
            print(
                f"  ⚠️ SESNSP: el corte más reciente es "
                f"{_MESES_ABREV[mejor_mes - 1]}{mejor_anio % 100:02d} — "
                f"el portal lleva {rezago} meses sin publicar"
            )
        return mejor_url

    def fetch_rows(
        self,
        claves_municipio: list[str],
        url: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> list[dict]:
        """
        Devuelve las filas (dicts) de los municipios pedidos.

        - local_path: lee un CSV ya descargado (drop manual o caché).
        - url: descarga en streaming desde esa URL.
        - Sin ambos: descubre la URL vigente en datos.gob.mx y descarga.
        """
        if local_path:
            with open(local_path, encoding="utf-8", errors="replace") as f:
                sample = f.read(200)
            encoding = "utf-8" if "Año" in sample else "latin-1"
            with open(local_path, encoding=encoding) as f:
                return self._filter(csv.reader(f), claves_municipio)

        if url is None:
            url = self.discover_url()
            if url:
                # El portal lista el corte con rezago: sondear meses más nuevos
                url = self.probe_beyond(url)
        if not url:
            return []

        print(f"  📥 SESNSP: descargando en streaming {url.rsplit('/', 1)[-1]}...")
        with requests.get(
            url, headers={"User-Agent": _BROWSER_UA}, stream=True, timeout=300
        ) as response:
            response.raise_for_status()
            # iter_lines (no TextIOWrapper sobre .raw): descomprime el gzip del
            # servidor y no lanza ValueError al EOF con urllib3 2.x.
            lines = response.iter_lines()
            first = next(lines, None)
            if first is None:
                return []
            # Sniff de encoding con el header: el SESNSP publica latin-1 hoy,
            # pero si cambia a utf-8 los filtros con acentos fallarían en silencio.
            encoding = "utf-8" if "Año" in first.decode("utf-8", errors="replace") else "latin-1"

            def decoded():
                yield first.decode(encoding)
                for ln in lines:
                    yield ln.decode(encoding)

            return self._filter(csv.reader(decoded()), claves_municipio)

    # ── Private ──────────────────────────────────────────────

    @staticmethod
    def _get_dataset_page() -> requests.Response:
        """
        GET a datos.gob.mx con fallback sin verificación SSL.

        La cadena de certificados de www.datos.gob.mx no incluye el intermedio,
        así que certifi puede fallar aunque el sitio sea legítimo. El fallback
        SOLO aplica a esta página de descubrimiento (un enlace público); la
        descarga del CSV en sí va contra repodatos.atdt.gob.mx con SSL completo.
        """
        try:
            response = requests.get(
                DATASET_PAGE, headers={"User-Agent": _BROWSER_UA}, timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            print("  ⚠️ SESNSP: cadena SSL incompleta en datos.gob.mx — reintentando sin verificación (solo descubrimiento)")
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(
                DATASET_PAGE, headers={"User-Agent": _BROWSER_UA}, timeout=30, verify=False
            )
            response.raise_for_status()
            return response

    @staticmethod
    def _filter(reader, claves_municipio: list[str]) -> list[dict]:
        header = next(reader, None)
        if header is None:  # CSV vacío o respuesta truncada
            return []
        claves = set(claves_municipio)
        # 'Cve. Municipio' es la columna 3 (índice); localizarla por nombre por robustez
        try:
            idx_cve = header.index("Cve. Municipio")
        except ValueError:
            idx_cve = 3

        rows = []
        for row in reader:
            if len(row) > idx_cve and row[idx_cve] in claves:
                rows.append(dict(zip(header, row)))
        return rows
