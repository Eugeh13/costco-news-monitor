"""HTML fixtures used across scraper tests."""

MILENIO_HTML = """
<html><body>
  <article class="card">
    <h2><a href="/estados/nuevo-leon/choque-multiple-carretera-nacional-2025">Choque múltiple en Carretera Nacional deja tres heridos</a></h2>
    <time datetime="2025-10-28T18:00:00-06:00">28 oct 2025</time>
    <p class="summary">Un choque múltiple en la Carretera Nacional dejó tres personas heridas esta tarde.</p>
  </article>
  <article class="card">
    <h2><a href="/ultima-hora/incendio-bodega-escobedo-2025">Incendio consume bodega en Escobedo</a></h2>
    <time datetime="2025-10-28T16:30:00-06:00">28 oct 2025</time>
    <p class="summary">Bomberos controlaron un incendio en una bodega del municipio de Escobedo.</p>
  </article>
</body></html>
"""

MILENIO_HTML_CHANGED_STRUCTURE = """
<html><body>
  <div class="card-item">
    <h3><a href="/nueva-estructura/noticia-ejemplo">Noticia con estructura nueva</a></h3>
    <span class="date">28/10/2025</span>
    <p>Descripción de la noticia con estructura ligeramente diferente.</p>
  </div>
</body></html>
"""

MILENIO_HTML_EMPTY = """
<html><body><div class="wrapper"><p>Sin noticias disponibles.</p></div></body></html>
"""

INFO7_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Info7 Monterrey</title>
    <link>https://www.info7.mx/monterrey/</link>
    <item>
      <title>Accidente vial en Constitución provoca caos vial</title>
      <link>https://www.info7.mx/monterrey/accidente-vial-constitucion/123</link>
      <pubDate>Tue, 28 Oct 2025 17:00:00 +0000</pubDate>
      <description>Un accidente en Av. Constitución generó caos en el tráfico vespertino.</description>
    </item>
    <item>
      <title>Balacera en Apodaca deja un muerto</title>
      <link>https://www.info7.mx/monterrey/balacera-apodaca/124</link>
      <pubDate>Tue, 28 Oct 2025 15:30:00 +0000</pubDate>
      <description>Elementos de seguridad acudieron al lugar del incidente.</description>
    </item>
  </channel>
</rss>
"""

INFO7_HTML = """
<html><body>
  <article class="noticia">
    <h2><a href="/monterrey/inundacion-san-nicolas">Inundación en San Nicolás tras tromba</a></h2>
    <time datetime="2025-10-28T14:00:00-06:00">28 oct 2025</time>
    <p class="resumen">Una tromba causó severas inundaciones en el municipio de San Nicolás.</p>
  </article>
</body></html>
"""

HORIZONTE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>El Horizonte</title>
    <link>https://www.elhorizonte.mx</link>
    <item>
      <title>Detienen a banda de robo de autos en Valle Oriente</title>
      <link>https://www.elhorizonte.mx/policiaca/banda-robo-autos/456</link>
      <pubDate>Tue, 28 Oct 2025 18:30:00 +0000</pubDate>
      <description>Elementos de la Fuerza Civil detuvieron a cuatro integrantes de una banda.</description>
    </item>
  </channel>
</rss>
"""

HORIZONTE_HTML = """
<html><body>
  <article class="nota">
    <h2><a href="/nuevo-leon/bloqueo-lazaro-cardenas">Bloqueo en Lázaro Cárdenas por manifestantes</a></h2>
    <time datetime="2025-10-28T12:00:00-06:00">28 oct 2025</time>
    <p class="bajada">Manifestantes cerraron Av. Lázaro Cárdenas durante dos horas.</p>
  </article>
</body></html>
"""

GNEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Protección Civil Nuevo León - Google News</title>
    <item>
      <title>Protección Civil NL atiende inundaciones en Monterrey - Milenio</title>
      <link>https://www.milenio.com/proteccion-civil-nl-inundaciones/999</link>
      <pubDate>Tue, 28 Oct 2025 20:00:00 +0000</pubDate>
      <description>Protección Civil de Nuevo León movilizó brigadas ante inundaciones.</description>
    </item>
    <item>
      <title>Alerta por fuertes lluvias en área metropolitana - El Horizonte</title>
      <link>https://www.elhorizonte.mx/alerta-lluvias/1001</link>
      <pubDate>Mon, 27 Oct 2025 10:00:00 +0000</pubDate>
      <description>Las autoridades emitieron alerta preventiva ante pronóstico de lluvias.</description>
    </item>
  </channel>
</rss>
"""
