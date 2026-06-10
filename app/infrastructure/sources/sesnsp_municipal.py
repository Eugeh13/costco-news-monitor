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
import io
import re
from typing import Optional

import requests

DATASET_PAGE = "https://www.datos.gob.mx/dataset/incidencia_delictiva"

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

        url = url or self.discover_url()
        if not url:
            return []

        print(f"  📥 SESNSP: descargando en streaming {url.rsplit('/', 1)[-1]}...")
        with requests.get(
            url, headers={"User-Agent": _BROWSER_UA}, stream=True, timeout=300
        ) as response:
            response.raise_for_status()
            # El SESNSP publica en latin-1/cp1252
            text = io.TextIOWrapper(response.raw, encoding="latin-1")
            return self._filter(csv.reader(text), claves_municipio)

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
        header = next(reader)
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
