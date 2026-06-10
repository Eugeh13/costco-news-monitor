"""
Tests de FileStorage.cleanup (app/infrastructure/persistence/file_storage.py).

Cubre el fix de Fase 2: cleanup conserva las entradas MÁS RECIENTES en orden
de inserción (antes el orden era aleatorio porque se reconstruía desde un
set, y podía borrar las recientes y conservar las viejas).

Todo trabaja sobre archivos temporales (tmp_path de pytest) — nada de red.
"""

from __future__ import annotations

from app.infrastructure.persistence.file_storage import FileStorage


def _urls(n: int) -> list[str]:
    return [f"https://ejemplo.test/nota-{i}" for i in range(n)]


def _storage_con(tmp_path, urls):
    fs = FileStorage(str(tmp_path / "processed_urls.txt"))
    for url in urls:
        fs.mark_processed(url)
    return fs


# ============================================================
# cleanup — elimina las más viejas, conserva las recientes en orden
# ============================================================

def test_cleanup_elimina_las_mas_viejas_y_conserva_orden(tmp_path):
    urls = _urls(10)
    fs = _storage_con(tmp_path, urls)

    removed = fs.cleanup(max_entries=4)

    assert removed == 6
    # El archivo conserva EXACTAMENTE las 4 más recientes, en orden de inserción
    assert (tmp_path / "processed_urls.txt").read_text(
        encoding="utf-8"
    ).splitlines() == urls[-4:]
    # Las viejas dejan de contar como procesadas; las recientes siguen
    assert all(not fs.is_processed(u) for u in urls[:6])
    assert all(fs.is_processed(u) for u in urls[-4:])


def test_cleanup_devuelve_cuantas_elimino(tmp_path):
    fs = _storage_con(tmp_path, _urls(7))
    assert fs.cleanup(max_entries=5) == 2


def test_cleanup_idempotente(tmp_path):
    urls = _urls(8)
    fs = _storage_con(tmp_path, urls)

    assert fs.cleanup(max_entries=3) == 5
    # Segunda pasada: ya no hay exceso → 0 y el archivo no cambia
    contenido = (tmp_path / "processed_urls.txt").read_text(encoding="utf-8")
    assert fs.cleanup(max_entries=3) == 0
    assert (tmp_path / "processed_urls.txt").read_text(encoding="utf-8") == contenido


def test_cleanup_sin_exceso_no_borra_nada(tmp_path):
    urls = _urls(3)
    fs = _storage_con(tmp_path, urls)

    assert fs.cleanup(max_entries=10) == 0
    assert (tmp_path / "processed_urls.txt").read_text(
        encoding="utf-8"
    ).splitlines() == urls


# ============================================================
# _load — el orden de inserción sobrevive al reload
# ============================================================

def test_reload_preserva_orden_tras_cleanup(tmp_path):
    urls = _urls(10)
    fs = _storage_con(tmp_path, urls)
    fs.cleanup(max_entries=4)

    # Nueva instancia desde el mismo archivo: mismo orden, mismas entradas
    fs2 = FileStorage(str(tmp_path / "processed_urls.txt"))
    assert fs2._order == urls[-4:]
    assert all(fs2.is_processed(u) for u in urls[-4:])
    assert all(not fs2.is_processed(u) for u in urls[:6])


def test_cleanup_tras_reload_sigue_borrando_las_viejas(tmp_path):
    """El orden persiste en disco: un cleanup posterior borra las correctas."""
    urls = _urls(6)
    _storage_con(tmp_path, urls)

    fs2 = FileStorage(str(tmp_path / "processed_urls.txt"))
    nueva = "https://ejemplo.test/nota-nueva"
    fs2.mark_processed(nueva)

    assert fs2.cleanup(max_entries=3) == 4
    # Conserva las 3 más recientes: las dos últimas viejas + la nueva
    assert (tmp_path / "processed_urls.txt").read_text(
        encoding="utf-8"
    ).splitlines() == [urls[4], urls[5], nueva]


def test_load_deduplica_conservando_primera_aparicion(tmp_path):
    archivo = tmp_path / "processed_urls.txt"
    archivo.write_text(
        "https://a.test/1\nhttps://a.test/2\nhttps://a.test/1\n\nhttps://a.test/3\n",
        encoding="utf-8",
    )
    fs = FileStorage(str(archivo))
    assert fs._order == [
        "https://a.test/1",
        "https://a.test/2",
        "https://a.test/3",
    ]


def test_archivo_inexistente_arranca_vacio(tmp_path):
    fs = FileStorage(str(tmp_path / "no-existe.txt"))
    assert fs._order == []
    assert fs.cleanup(max_entries=5) == 0
