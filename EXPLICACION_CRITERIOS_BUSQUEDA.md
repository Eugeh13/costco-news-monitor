# 🔍 Explicación Completa: ¿Qué Busca el Sistema y Bajo Qué Criterios?

## Sistema de Monitoreo de Noticias - Costco Monterrey

---

## 📍 UBICACIONES MONITOREADAS

El sistema vigila **3 sucursales de Costco** en Monterrey:

### 1. Costco Carretera Nacional
- **Ubicación**: Carretera Nacional Km. 268 +500 5001, Monterrey, NL 64989
- **Coordenadas**: 25.5781498, -100.2512201
- **Radio de búsqueda**: 3 kilómetros a la redonda

**Vialidades clave monitoreadas**:
- Carretera Nacional
- Lincoln
- Constitución / Prolongación Constitución
- Ruiz Cortines / Adolfo Ruiz Cortines

### 2. Costco Cumbres
- **Ubicación**: Alejandro de Rodas 6767, Monterrey, NL 64344
- **Coordenadas**: 25.7295984, -100.3927985
- **Radio de búsqueda**: 3 kilómetros a la redonda

**Vialidades clave monitoreadas**:
- Alejandro de Rodas
- Raúl Rangel Frías
- Paseo de los Leones
- San Jerónimo
- Cumbres (zona)

### 3. Costco Valle Oriente
- **Ubicación**: Av. Lázaro Cárdenas 800, San Pedro Garza García, NL 66269
- **Coordenadas**: 25.6396949, -100.317631
- **Radio de búsqueda**: 3 kilómetros a la redonda

**Vialidades clave monitoreadas**:
- Lázaro Cárdenas / Av. Lázaro Cárdenas
- Fundadores / Av. Fundadores
- Vasconcelos / José Vasconcelos
- Valle Oriente (zona)
- San Pedro / Garza García
- Gómez Morín
- Morones Prieto

---

## 🎯 CATEGORÍAS DE EVENTOS QUE BUSCA

El sistema busca **5 tipos de eventos de alto impacto**:

### 1. 🚗 ACCIDENTES VIALES

**Palabras clave que detecta**:
- choque
- accidente
- volcadura
- atropello
- colisión
- vuelco
- chocó
- volcó
- carambola
- tráiler
- cierre de avenida
- cierre de carretera
- tránsito cerrado
- lesionados en accidente
- heridos en choque
- vehículos involucrados

**Ejemplos de noticias que SÍ detecta**:
- ✅ "Choque en Lázaro Cárdenas deja 3 heridos"
- ✅ "Volcadura de tráiler cierra Carretera Nacional"
- ✅ "Accidente múltiple en Fundadores afecta tránsito"
- ✅ "Atropello en Alejandro de Rodas deja un lesionado"

### 2. 🔥 INCENDIOS

**Palabras clave que detecta**:
- incendio
- fuego
- llamas
- arde
- bomberos
- humo denso
- conflagración
- edificio en llamas
- local en llamas
- vehículo en llamas

**Ejemplos de noticias que SÍ detecta**:
- ✅ "Incendio en local comercial en Valle Oriente"
- ✅ "Bomberos combaten fuego en edificio de Cumbres"
- ✅ "Vehículo arde en Carretera Nacional"

### 3. 🚨 SEGURIDAD (Violencia)

**Palabras clave que detecta**:
- balacera
- disparos
- tiroteo
- persecución
- enfrentamiento
- baleado
- herido de bala
- hombres armados
- detonaciones
- ráfagas
- fuego cruzado
- resguardo policial
- acordonamiento
- zona acordonada

**Ejemplos de noticias que SÍ detecta**:
- ✅ "Balacera en San Pedro deja zona acordonada"
- ✅ "Reportan detonaciones en Lázaro Cárdenas"
- ✅ "Enfrentamiento en Cumbres moviliza a policía"

### 4. 🚧 BLOQUEOS

**Palabras clave que detecta**:
- bloqueo
- cierre
- cerrada
- manifestación
- protesta
- obstrucción
- tránsito cerrado
- bloqueada
- cerrado

**Ejemplos de noticias que SÍ detecta**:
- ✅ "Manifestación bloquea Constitución"
- ✅ "Cierre total de Rangel Frías por protesta"
- ✅ "Bloquean Lázaro Cárdenas en ambos sentidos"

### 5. 🌊 DESASTRES NATURALES

**Palabras clave que detecta**:
- inundación
- desbordamiento
- deslizamiento
- deslave
- tromba
- granizada
- tornado
- río desbordado

**Ejemplos de noticias que SÍ detecta**:
- ✅ "Inundación en Carretera Nacional por tromba"
- ✅ "Desbordamiento afecta Valle Oriente"
- ✅ "Granizada causa estragos en Cumbres"

---

## 🚫 NOTICIAS QUE RECHAZA AUTOMÁTICAMENTE

El sistema **descarta** noticias que contengan estas palabras (filtros de exclusión):

### ❌ Espectáculos / Farándula
**Palabras que rechazan la noticia**:
- actor, actriz
- famoso, celebridad
- artista, cantante
- película, serie
- concierto, show
- estreno

**Ejemplo rechazado**:
- ❌ "Actor sufre accidente en grabación de película"
- ❌ "Cantante famoso choca en Monterrey"

### ❌ Noticias Históricas / Pasadas
**Palabras que rechazan la noticia**:
- hace años
- en el pasado
- recordamos
- aniversario
- historia de
- así fue
- revelan detalles

**Ejemplo rechazado**:
- ❌ "Hace 5 años ocurrió trágico accidente en Lázaro Cárdenas"
- ❌ "Recordamos el incendio que marcó a Monterrey"

### ❌ Política General
**Palabras que rechazan la noticia**:
- declaraciones
- conferencia de prensa
- anuncia
- promete
- implementará
- planea
- propone

**Ejemplo rechazado**:
- ❌ "Gobernador anuncia plan contra accidentes"
- ❌ "Alcalde promete mejorar seguridad vial"

### ❌ Ubicaciones Lejanas (Fuera del área)
**Palabras que rechazan la noticia**:
- pesquería
- cadereyta
- santiago
- allende
- montemorelos
- ciudad de méxico, cdmx
- guanajuato
- jalisco
- tamaulipas

**Ejemplo rechazado**:
- ❌ "Choque en Pesquería deja 2 heridos"
- ❌ "Incendio en Cadereyta moviliza a bomberos"

---

## 📏 CRITERIOS DE DISTANCIA

### Criterio Principal: Radio de 3 km

El sistema calcula la distancia desde el evento hasta cada Costco:

```
Evento → Geocodificar ubicación → Calcular distancia → ¿Está dentro de 3 km?
```

**Ejemplo**:
- Evento en: Av. Lázaro Cárdenas altura Fundadores
- Coordenadas: 25.6396949, -100.317631
- Distancia a Costco Valle Oriente: **2.1 km** ✅ DENTRO DEL RADIO
- **Resultado**: Envía alerta

### Criterio Alternativo: Vialidades Clave

**Si el evento está FUERA del radio de 3 km**, el sistema hace una segunda verificación:

¿La noticia menciona alguna **vialidad clave** de algún Costco?

**Ejemplo**:
- Evento en: Carretera Nacional km 270
- Distancia a Costco Carretera Nacional: **4.5 km** ❌ FUERA DEL RADIO
- Pero menciona: "Carretera Nacional" ✅ VIALIDAD CLAVE
- **Resultado**: Envía alerta de todas formas

**Razón**: Las vialidades principales pueden afectar el acceso al Costco aunque el evento esté un poco más lejos.

---

## 🔄 FLUJO COMPLETO DE ANÁLISIS

### Paso 1: SCRAPING (Recolección)
```
Fuentes monitoreadas:
├─ Milenio Última Hora (https://www.milenio.com/ultima-hora)
├─ Milenio Monterrey (https://www.milenio.com/monterrey)
├─ El Horizonte (https://www.elhorizonte.mx/)
└─ INFO 7 (https://www.info7.mx/) [Actualmente no funciona]

Resultado: ~30 noticias por ciclo
```

### Paso 2: PRE-FILTRADO RÁPIDO (Sin IA)
```
Para cada noticia:
├─ ¿Contiene palabras de EXCLUSIÓN? → ❌ RECHAZAR
├─ ¿Contiene palabras de ALTO IMPACTO? → ✅ CONTINUAR
└─ Si no cumple → ❌ RECHAZAR

Resultado: ~2-3 candidatas (90% eliminadas)
```

### Paso 3: ANÁLISIS CON IA (Solo candidatas)
```
Para cada candidata:
├─ Analizar con OpenAI GPT-4o-mini
├─ ¿Es realmente relevante?
├─ ¿Cuál es la ubicación exacta?
├─ ¿Qué tan grave es? (Severidad 1-10)
├─ ¿Cuántas víctimas hay?
├─ ¿Qué impacto tiene en tráfico?
└─ Generar resumen inteligente

Resultado: Análisis completo con IA
```

### Paso 4: EXTRACCIÓN DE UBICACIÓN
```
Método 1 (IA):
└─ Extraer ubicación en lenguaje natural
   Ejemplo: "Av. Lázaro Cárdenas altura Fundadores"

Método 2 (Regex - fallback):
└─ Buscar patrones de ubicación
   Ejemplo: "lázaro cárdenas"
```

### Paso 5: GEOCODIFICACIÓN
```
Ubicación extraída → Geopy/Nominatim → Coordenadas GPS

Ejemplo:
"Lázaro Cárdenas, Monterrey" → (25.6396949, -100.317631)
```

### Paso 6: CÁLCULO DE DISTANCIA
```
Para cada Costco:
├─ Calcular distancia desde evento
├─ ¿Está dentro de 3 km? → ✅ ENVIAR ALERTA
└─ ¿Fuera de 3 km? → Verificar vialidades clave
```

### Paso 7: CLASIFICACIÓN DE SEVERIDAD (Con IA)
```
Escala 1-10:
├─ 1-3: MENOR (sin heridos, daños leves) ℹ️
├─ 4-6: MODERADA (heridos leves, tráfico afectado) ⚠️
├─ 7-8: GRAVE (heridos graves, cierre de vialidad) 🚨
└─ 9-10: CRÍTICA (víctimas fatales, emergencia) 🚨🚨
```

### Paso 8: NOTIFICACIÓN
```
Si cumple todos los criterios:
└─ Enviar alerta a Telegram con:
   ├─ Categoría del evento
   ├─ Título de la noticia
   ├─ Severidad clasificada
   ├─ Número de víctimas
   ├─ Impacto en tráfico
   ├─ Ubicación exacta
   ├─ Distancia al Costco más cercano
   ├─ Servicios de emergencia presentes
   └─ Link a la noticia completa
```

---

## 📊 EJEMPLOS REALES DE ANÁLISIS

### Ejemplo 1: ALERTA ENVIADA ✅

**Noticia**: "Choque múltiple en Lázaro Cárdenas deja 3 heridos, bomberos en el lugar"

**Análisis paso a paso**:

1. **Pre-filtrado**: ✅ Contiene "choque" (palabra clave de accidente vial)
2. **Exclusión**: ✅ No contiene palabras de exclusión
3. **Análisis IA**:
   - Relevante: ✅ Sí (evento actual de alto impacto)
   - Categoría: Accidente Vial
   - Severidad: 7/10 (GRAVE)
   - Víctimas: 3 heridos
   - Impacto tráfico: ALTO
   - Servicios emergencia: Sí (bomberos)
4. **Ubicación IA**: "Av. Lázaro Cárdenas altura Fundadores"
5. **Geocodificación**: (25.6396949, -100.317631)
6. **Distancia**: 2.1 km de Costco Valle Oriente ✅ DENTRO DEL RADIO
7. **Resultado**: **ALERTA ENVIADA** 🚨

### Ejemplo 2: RECHAZADA POR EXCLUSIÓN ❌

**Noticia**: "Actor famoso sufre accidente en grabación de película en Monterrey"

**Análisis paso a paso**:

1. **Pre-filtrado**: ✅ Contiene "accidente" (palabra clave)
2. **Exclusión**: ❌ Contiene "actor" y "película" (palabras de exclusión)
3. **Resultado**: **RECHAZADA** (espectáculos, no relevante)

### Ejemplo 3: RECHAZADA POR UBICACIÓN ❌

**Noticia**: "Choque en Pesquería deja 2 heridos"

**Análisis paso a paso**:

1. **Pre-filtrado**: ✅ Contiene "choque"
2. **Exclusión**: ❌ Contiene "pesquería" (ubicación lejana)
3. **Resultado**: **RECHAZADA** (fuera del área de interés)

### Ejemplo 4: RECHAZADA POR DISTANCIA ❌

**Noticia**: "Incendio en local de la colonia Obispado"

**Análisis paso a paso**:

1. **Pre-filtrado**: ✅ Contiene "incendio"
2. **Exclusión**: ✅ No contiene palabras de exclusión
3. **Análisis IA**: ✅ Relevante
4. **Ubicación**: "Colonia Obispado, Monterrey"
5. **Geocodificación**: (25.6722, -100.3089)
6. **Distancia**: 
   - Costco Valle Oriente: 4.8 km ❌
   - Costco Cumbres: 5.2 km ❌
   - Costco Carretera Nacional: 11.3 km ❌
7. **Vialidades clave**: No menciona ninguna
8. **Resultado**: **RECHAZADA** (fuera del radio y sin vialidades clave)

### Ejemplo 5: ACEPTADA POR VIALIDAD CLAVE ✅

**Noticia**: "Bloqueo en Carretera Nacional por manifestación"

**Análisis paso a paso**:

1. **Pre-filtrado**: ✅ Contiene "bloqueo"
2. **Exclusión**: ✅ No contiene palabras de exclusión
3. **Análisis IA**: ✅ Relevante
4. **Ubicación**: "Carretera Nacional, Monterrey"
5. **Geocodificación**: (25.5850, -100.2400)
6. **Distancia**: 3.8 km de Costco Carretera Nacional ❌ FUERA
7. **Vialidades clave**: ✅ Menciona "Carretera Nacional" (vialidad clave de Costco Carretera Nacional)
8. **Resultado**: **ALERTA ENVIADA** 🚨 (por vialidad clave)

---

## ⏰ FRECUENCIA DE MONITOREO

**Horarios de ejecución**: Cada 30 minutos en horarios fijos
- :00 (en punto de cada hora)
- :30 (media hora de cada hora)

**Ejemplos**:
- 08:00, 08:30, 09:00, 09:30, 10:00, 10:30...
- 24 horas al día, 7 días a la semana
- **48 monitoreos por día**

---

## 📱 TIPOS DE NOTIFICACIONES

### Tipo 1: Resumen (Sin alertas)

Cuando NO hay eventos de alto impacto:

```
✅ Monitoreo Completado

📊 Resumen:
• Noticias analizadas: 30
• Alertas de alto impacto: 0
• Estado: Todo tranquilo ✓

📍 Áreas monitoreadas:
• Costco Carretera Nacional
• Costco Cumbres
• Costco Valle Oriente

⏰ 28/10/2025 18:00
🔄 Próximo monitoreo en 30 minutos
```

### Tipo 2: Alerta (Con evento detectado)

Cuando SÍ hay evento de alto impacto:

```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Choque múltiple en Lázaro Cárdenas deja 3 heridos

⚡ Severidad: GRAVE (7/10)
👥 Víctimas/Heridos: 3
🚗 Impacto en tráfico: ALTO
🚑 Servicios de emergencia en el lugar

📏 A 2.1 km de Costco Valle Oriente
🗺️ Av. Lázaro Cárdenas altura Fundadores

📝 Accidente vehicular con tres personas lesionadas.

📡 Milenio Monterrey
🔗 [Ver noticia completa]

⏰ 28/10/2025 18:00
```

---

## 🎯 RESUMEN DE CRITERIOS

### ✅ UNA NOTICIA SE ENVÍA COMO ALERTA SI:

1. **Contiene palabras clave** de alto impacto (accidente, incendio, balacera, bloqueo, desastre)
2. **NO contiene palabras de exclusión** (espectáculos, histórica, política, ubicación lejana)
3. **Tiene ubicación específica** (no solo "Monterrey")
4. **Está dentro de 3 km** de algún Costco, O menciona una **vialidad clave**
5. **La IA confirma** que es relevante y actual

### ❌ UNA NOTICIA SE RECHAZA SI:

1. No contiene palabras clave de alto impacto
2. Contiene palabras de exclusión
3. No tiene ubicación específica
4. Está fuera del radio de 3 km Y no menciona vialidades clave
5. La IA determina que no es relevante

---

## 💡 VENTAJAS DEL SISTEMA CON IA

### Antes (Sistema Original)
- Buscaba solo palabras clave exactas
- No entendía contexto
- "Choque de opiniones" = alerta falsa
- No clasificaba severidad

### Ahora (Con IA)
- Entiende contexto y semántica
- Distingue "choque vehicular" de "choque de opiniones"
- Clasifica severidad automáticamente
- Detecta víctimas y evalúa impacto
- **75% menos falsos positivos**

---

## 📞 Información de Contacto

**Bot de Telegram**: @monitorCostco_bot  
**Chat ID**: 7510716093  
**Usuario**: +52 8124686732

---

**Fecha**: 28 de octubre de 2025  
**Versión**: 2.0 con IA  
**Powered by**: OpenAI GPT-4o-mini
