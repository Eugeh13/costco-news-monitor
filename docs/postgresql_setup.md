# 🗄️ Guía de Configuración de PostgreSQL en Railway

## 📋 Resumen

Esta guía te ayudará a configurar la base de datos PostgreSQL en Railway para el sistema de monitoreo de noticias de Costco Monterrey. La base de datos permitirá:

- ✅ **Evitar duplicados** entre diferentes fuentes de noticias
- ✅ **Guardar todas las noticias** procesadas con información completa
- ✅ **Tracking histórico** para análisis y dashboards futuros
- ✅ **Detección inteligente** de noticias duplicadas usando hash de contenido

---

## 🚀 Paso 1: Crear Base de Datos PostgreSQL en Railway

### 1.1 Acceder a tu proyecto en Railway

1. Ve a [Railway.app](https://railway.app/)
2. Inicia sesión con tu cuenta
3. Abre tu proyecto **costco-news-monitor**

### 1.2 Agregar servicio PostgreSQL

1. En tu proyecto, haz clic en **"+ New"**
2. Selecciona **"Database"**
3. Elige **"PostgreSQL"**
4. Railway creará automáticamente una base de datos PostgreSQL

### 1.3 Esperar a que se despliegue

- El servicio PostgreSQL tardará unos 30-60 segundos en estar listo
- Verás un indicador verde cuando esté activo

---

## 🔧 Paso 2: Configurar Variable de Entorno

### 2.1 Obtener la URL de conexión

1. Haz clic en el servicio **PostgreSQL** que acabas de crear
2. Ve a la pestaña **"Variables"**
3. Busca la variable **`DATABASE_URL`**
4. Copia el valor completo (debe verse algo como: `postgresql://postgres:password@hostname:5432/railway`)

### 2.2 Agregar DATABASE_URL a tu aplicación

1. Haz clic en tu servicio de aplicación (el que ejecuta el código Python)
2. Ve a la pestaña **"Variables"**
3. Haz clic en **"+ New Variable"**
4. Agrega:
   - **Nombre:** `DATABASE_URL`
   - **Valor:** Pega la URL que copiaste en el paso anterior

### 2.3 Guardar cambios

- Railway guardará automáticamente
- La aplicación se redesplegará con la nueva variable

---

## 📊 Paso 3: Crear la Tabla de Noticias

### 3.1 Conectarse a PostgreSQL

Tienes dos opciones:

#### Opción A: Usar Railway CLI (Recomendado)

```bash
# Instalar Railway CLI si no lo tienes
npm i -g @railway/cli

# Iniciar sesión
railway login

# Conectar a tu proyecto
railway link

# Conectar a PostgreSQL
railway connect postgres
```

#### Opción B: Usar cliente PostgreSQL externo

1. En Railway, ve al servicio PostgreSQL
2. Pestaña **"Connect"**
3. Copia las credenciales (host, port, user, password, database)
4. Usa un cliente como [pgAdmin](https://www.pgadmin.org/) o [DBeaver](https://dbeaver.io/)

### 3.2 Ejecutar el script SQL

Una vez conectado a PostgreSQL, ejecuta el siguiente script:

```sql
-- Crear tabla de noticias con todos los campos necesarios
CREATE TABLE IF NOT EXISTS noticias (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(500) NOT NULL,
    tipo_evento VARCHAR(100) NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    url VARCHAR(1000),
    descripcion TEXT,
    costco_impactado VARCHAR(100) NOT NULL,
    fuente VARCHAR(100) NOT NULL,
    severidad INTEGER DEFAULT 5,
    ubicacion_extraida VARCHAR(500),
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    distancia_km DECIMAL(5, 2),
    victimas INTEGER DEFAULT 0,
    impacto_trafico VARCHAR(50),
    servicios_emergencia BOOLEAN DEFAULT FALSE,
    hash_contenido VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hash_contenido)
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_fecha_hora ON noticias(fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_hash_contenido ON noticias(hash_contenido);
CREATE INDEX IF NOT EXISTS idx_costco_impactado ON noticias(costco_impactado);
CREATE INDEX IF NOT EXISTS idx_tipo_evento ON noticias(tipo_evento);
CREATE INDEX IF NOT EXISTS idx_severidad ON noticias(severidad DESC);
CREATE INDEX IF NOT EXISTS idx_created_at ON noticias(created_at DESC);

-- Verificar que la tabla se creó correctamente
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'noticias'
ORDER BY ordinal_position;
```

### 3.3 Verificar creación exitosa

Deberías ver una lista de todas las columnas de la tabla `noticias`.

---

## ✅ Paso 4: Verificar que Todo Funciona

### 4.1 Revisar logs de Railway

1. Ve a tu servicio de aplicación en Railway
2. Pestaña **"Deployments"**
3. Haz clic en el deployment más reciente
4. Revisa los logs

### 4.2 Buscar mensajes de confirmación

Deberías ver en los logs:

```
✓ Base de datos PostgreSQL conectada
✓ Tabla 'noticias' verificada/creada
```

Si ves errores, verifica:
- Que `DATABASE_URL` esté correctamente configurada
- Que la tabla `noticias` exista en la base de datos
- Que el servicio PostgreSQL esté activo

### 4.3 Esperar al próximo ciclo de monitoreo

El sistema se ejecuta cada 30 minutos (en punto y media).

Cuando se procese una noticia, verás en los logs:

```
📰 Candidata detectada: [título]...
   🤖 Analizando con IA...
   ✓ Relevante - Categoría: [categoría]
   ⚡ Severidad: [X]/10
   📍 Ubicación: [ubicación]
   🗺️  Coordenadas: [lat], [lon]
   ✓ Dentro del radio: [X] km de [Costco]
   💾 Guardada en base de datos
```

---

## 📊 Paso 5: Consultar la Base de Datos

### Consultas útiles para análisis

#### Ver todas las noticias guardadas

```sql
SELECT id, titulo, tipo_evento, fecha_hora, costco_impactado, severidad, fuente
FROM noticias
ORDER BY fecha_hora DESC
LIMIT 50;
```

#### Contar noticias por tipo de evento

```sql
SELECT tipo_evento, COUNT(*) as total
FROM noticias
GROUP BY tipo_evento
ORDER BY total DESC;
```

#### Noticias por Costco impactado

```sql
SELECT costco_impactado, COUNT(*) as total
FROM noticias
GROUP BY costco_impactado
ORDER BY total DESC;
```

#### Noticias de alta severidad (≥7)

```sql
SELECT titulo, tipo_evento, severidad, costco_impactado, fecha_hora
FROM noticias
WHERE severidad >= 7
ORDER BY severidad DESC, fecha_hora DESC;
```

#### Noticias de las últimas 24 horas

```sql
SELECT titulo, tipo_evento, fecha_hora, costco_impactado, fuente
FROM noticias
WHERE fecha_hora >= NOW() - INTERVAL '24 hours'
ORDER BY fecha_hora DESC;
```

#### Estadísticas por fuente

```sql
SELECT fuente, COUNT(*) as total, AVG(severidad) as severidad_promedio
FROM noticias
GROUP BY fuente
ORDER BY total DESC;
```

#### Detectar duplicados (mismo hash)

```sql
SELECT hash_contenido, COUNT(*) as veces_detectado, 
       MIN(fecha_hora) as primera_vez, MAX(fecha_hora) as ultima_vez
FROM noticias
GROUP BY hash_contenido
HAVING COUNT(*) > 1
ORDER BY veces_detectado DESC;
```

---

## 🔍 Verificación de Duplicados

### Cómo funciona la detección

El sistema genera un **hash SHA-256** del contenido normalizado de cada noticia:

1. Se normaliza el título y descripción (minúsculas, sin acentos, sin puntuación)
2. Se genera un hash único del contenido
3. Antes de procesar, se verifica si existe ese hash en las últimas 24 horas
4. Si existe, se descarta como duplicado
5. Si no existe, se procesa y guarda

### Verificar duplicados manualmente

```sql
-- Ver noticias con el mismo hash
SELECT titulo, fuente, fecha_hora, hash_contenido
FROM noticias
WHERE hash_contenido IN (
    SELECT hash_contenido
    FROM noticias
    GROUP BY hash_contenido
    HAVING COUNT(*) > 1
)
ORDER BY hash_contenido, fecha_hora;
```

---

## 🎯 Campos de la Tabla

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | ID único autoincremental |
| `titulo` | VARCHAR(500) | Título de la noticia |
| `tipo_evento` | VARCHAR(100) | Categoría (accidente, incendio, balacera, etc.) |
| `fecha_hora` | TIMESTAMP | Fecha y hora del evento |
| `url` | VARCHAR(1000) | URL de la noticia original |
| `descripcion` | TEXT | Resumen o descripción completa |
| `costco_impactado` | VARCHAR(100) | Nombre del Costco cercano |
| `fuente` | VARCHAR(100) | Fuente de la noticia (Milenio, Twitter, etc.) |
| `severidad` | INTEGER | Nivel de severidad 1-10 (analizado por IA) |
| `ubicacion_extraida` | VARCHAR(500) | Ubicación extraída del texto |
| `latitud` | DECIMAL(10,8) | Coordenada latitud |
| `longitud` | DECIMAL(11,8) | Coordenada longitud |
| `distancia_km` | DECIMAL(5,2) | Distancia al Costco más cercano |
| `victimas` | INTEGER | Número de víctimas (analizado por IA) |
| `impacto_trafico` | VARCHAR(50) | Impacto en tráfico (analizado por IA) |
| `servicios_emergencia` | BOOLEAN | Si hay servicios de emergencia presentes |
| `hash_contenido` | VARCHAR(64) | Hash SHA-256 para detección de duplicados |
| `created_at` | TIMESTAMP | Fecha de creación del registro |

---

## 🚨 Solución de Problemas

### Error: "could not connect to server"

**Causa:** La variable `DATABASE_URL` no está configurada o es incorrecta.

**Solución:**
1. Verifica que `DATABASE_URL` esté en las variables de entorno
2. Verifica que el servicio PostgreSQL esté activo
3. Redespliega la aplicación

### Error: "relation 'noticias' does not exist"

**Causa:** La tabla no se ha creado en la base de datos.

**Solución:**
1. Conéctate a PostgreSQL (ver Paso 3)
2. Ejecuta el script SQL completo
3. Verifica con: `\dt` (en psql) o consulta SQL

### No se guardan noticias en la DB

**Causa:** El sistema no está encontrando noticias relevantes o hay error en la conexión.

**Solución:**
1. Revisa los logs de Railway
2. Busca mensajes de error relacionados con PostgreSQL
3. Verifica que `self.database.enabled` sea `True` en los logs
4. Espera a que haya noticias relevantes en el próximo ciclo

### Duplicados no se están detectando

**Causa:** El hash puede estar generándose diferente entre fuentes.

**Solución:**
1. Consulta la tabla para ver los hashes guardados
2. Verifica que noticias similares tengan hashes diferentes
3. Ajusta la normalización en `database.py` si es necesario

---

## 📈 Próximos Pasos (Dashboards)

Con la base de datos configurada, podrás crear:

### Dashboard de Monitoreo en Tiempo Real
- Noticias de las últimas 24 horas
- Mapa de calor con ubicaciones
- Gráficas de severidad por Costco

### Análisis Histórico
- Tendencias por tipo de evento
- Horarios de mayor incidencia
- Zonas más afectadas

### Reportes Automatizados
- Resumen semanal/mensual
- Comparativas entre Costcos
- Estadísticas de fuentes más confiables

### Herramientas sugeridas:
- **Metabase** (open source, fácil de usar)
- **Grafana** (visualizaciones avanzadas)
- **Streamlit** (dashboards en Python)
- **Power BI** / **Tableau** (enterprise)

---

## 📞 Soporte

Si tienes problemas con la configuración:

1. Revisa los logs de Railway cuidadosamente
2. Verifica cada paso de esta guía
3. Consulta la documentación de Railway: https://docs.railway.app/
4. Revisa el código en `database.py` para entender la lógica

---

## ✅ Checklist de Configuración

- [ ] Servicio PostgreSQL creado en Railway
- [ ] Variable `DATABASE_URL` configurada en la aplicación
- [ ] Tabla `noticias` creada con el script SQL
- [ ] Índices creados correctamente
- [ ] Aplicación redesplegada con la nueva configuración
- [ ] Logs muestran conexión exitosa a PostgreSQL
- [ ] Primera noticia guardada exitosamente
- [ ] Detección de duplicados funcionando

---

**¡Listo!** Tu sistema ahora tiene persistencia completa y detección de duplicados. 🎉
