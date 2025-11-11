-- ============================================================================
-- ESQUEMA DE BASE DE DATOS PARA SISTEMA DE MONITOREO DE NOTICIAS
-- ============================================================================

-- Tabla principal de noticias detectadas
CREATE TABLE IF NOT EXISTS noticias (
    -- Identificación
    id SERIAL PRIMARY KEY,
    noticia_hash VARCHAR(64) UNIQUE NOT NULL,  -- Hash único para detectar duplicados
    
    -- Información básica
    titulo TEXT NOT NULL,
    descripcion TEXT,
    url TEXT NOT NULL,
    fuente VARCHAR(100) NOT NULL,  -- 'Milenio', 'El Horizonte', 'Twitter:@pc_mty', etc.
    
    -- Clasificación
    categoria VARCHAR(50) NOT NULL,  -- 'accidente_vial', 'incendio', 'seguridad', 'bloqueo', 'desastre_natural'
    severidad INTEGER CHECK (severidad BETWEEN 1 AND 10),  -- Clasificación de IA
    
    -- Ubicación
    ubicacion_texto TEXT,  -- Texto original de la ubicación
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    
    -- Costco impactado
    costco_nombre VARCHAR(100),  -- 'Costco Carretera Nacional', 'Costco Cumbres', etc.
    costco_distancia_km DECIMAL(5, 2),  -- Distancia en kilómetros
    
    -- Detalles del evento (análisis de IA)
    victimas INTEGER DEFAULT 0,
    heridos INTEGER DEFAULT 0,
    impacto_trafico VARCHAR(20),  -- 'ALTO', 'MEDIO', 'BAJO', NULL
    servicios_emergencia BOOLEAN DEFAULT FALSE,
    
    -- Timestamps (en zona horaria CST)
    fecha_evento TIMESTAMP WITH TIME ZONE,  -- Cuándo ocurrió el evento
    fecha_publicacion TIMESTAMP WITH TIME ZONE,  -- Cuándo se publicó la noticia
    fecha_deteccion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- Cuándo la detectamos
    
    -- Metadata
    alerta_enviada BOOLEAN DEFAULT FALSE,
    fecha_alerta TIMESTAMP WITH TIME ZONE,
    
    -- Índices para búsquedas rápidas
    CONSTRAINT unique_url_fuente UNIQUE (url, fuente)
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_noticias_fecha_evento ON noticias(fecha_evento DESC);
CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);
CREATE INDEX IF NOT EXISTS idx_noticias_costco ON noticias(costco_nombre);
CREATE INDEX IF NOT EXISTS idx_noticias_hash ON noticias(noticia_hash);
CREATE INDEX IF NOT EXISTS idx_noticias_fecha_deteccion ON noticias(fecha_deteccion DESC);

-- Tabla de fuentes monitoreadas (para tracking)
CREATE TABLE IF NOT EXISTS fuentes_monitoreo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    tipo VARCHAR(20) NOT NULL,  -- 'portal', 'twitter'
    url TEXT,
    activa BOOLEAN DEFAULT TRUE,
    ultima_consulta TIMESTAMP WITH TIME ZONE,
    total_noticias_detectadas INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de ejecuciones del monitoreo (para tracking)
CREATE TABLE IF NOT EXISTS ejecuciones_monitoreo (
    id SERIAL PRIMARY KEY,
    fecha_inicio TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_fin TIMESTAMP WITH TIME ZONE,
    noticias_analizadas INTEGER DEFAULT 0,
    noticias_nuevas INTEGER DEFAULT 0,
    noticias_duplicadas INTEGER DEFAULT 0,
    alertas_enviadas INTEGER DEFAULT 0,
    estado VARCHAR(20),  -- 'completado', 'error', 'en_proceso'
    mensaje_error TEXT
);

-- Vista para dashboard: Noticias recientes por categoría
CREATE OR REPLACE VIEW vista_noticias_recientes AS
SELECT 
    categoria,
    COUNT(*) as total,
    COUNT(CASE WHEN alerta_enviada THEN 1 END) as con_alerta,
    AVG(severidad) as severidad_promedio,
    MAX(fecha_evento) as ultima_ocurrencia
FROM noticias
WHERE fecha_evento >= NOW() - INTERVAL '7 days'
GROUP BY categoria
ORDER BY total DESC;

-- Vista para dashboard: Impacto por Costco
CREATE OR REPLACE VIEW vista_impacto_por_costco AS
SELECT 
    costco_nombre,
    COUNT(*) as total_eventos,
    AVG(severidad) as severidad_promedio,
    AVG(costco_distancia_km) as distancia_promedio_km,
    COUNT(CASE WHEN categoria = 'accidente_vial' THEN 1 END) as accidentes,
    COUNT(CASE WHEN categoria = 'incendio' THEN 1 END) as incendios,
    COUNT(CASE WHEN categoria = 'seguridad' THEN 1 END) as seguridad,
    MAX(fecha_evento) as ultimo_evento
FROM noticias
WHERE costco_nombre IS NOT NULL
  AND fecha_evento >= NOW() - INTERVAL '30 days'
GROUP BY costco_nombre
ORDER BY total_eventos DESC;

-- Vista para dashboard: Estadísticas por fuente
CREATE OR REPLACE VIEW vista_estadisticas_fuentes AS
SELECT 
    fuente,
    COUNT(*) as total_noticias,
    COUNT(CASE WHEN alerta_enviada THEN 1 END) as alertas_generadas,
    AVG(severidad) as severidad_promedio,
    MIN(fecha_deteccion) as primera_deteccion,
    MAX(fecha_deteccion) as ultima_deteccion
FROM noticias
GROUP BY fuente
ORDER BY total_noticias DESC;

-- Comentarios para documentación
COMMENT ON TABLE noticias IS 'Almacena todas las noticias de alto impacto detectadas por el sistema';
COMMENT ON COLUMN noticias.noticia_hash IS 'Hash MD5 del título normalizado para detectar duplicados';
COMMENT ON COLUMN noticias.categoria IS 'Tipo de evento: accidente_vial, incendio, seguridad, bloqueo, desastre_natural';
COMMENT ON COLUMN noticias.severidad IS 'Clasificación de 1-10 generada por IA';
COMMENT ON COLUMN noticias.fecha_evento IS 'Timestamp del evento real (cuando ocurrió)';
COMMENT ON COLUMN noticias.fecha_publicacion IS 'Timestamp de publicación de la noticia';
COMMENT ON COLUMN noticias.fecha_deteccion IS 'Timestamp de cuando nuestro sistema la detectó';
