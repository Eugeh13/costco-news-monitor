# 🤖 Guía de Mejoras con Inteligencia Artificial

## Sistema de Monitoreo de Noticias - Costco Monterrey
### Versión Mejorada con OpenAI

---

## 📋 Resumen de Mejoras

El sistema ha sido mejorado con análisis de **Inteligencia Artificial usando OpenAI** para proporcionar:

✅ **Análisis inteligente de noticias** - Comprensión de contexto y semántica  
✅ **Extracción precisa de ubicaciones** - Detecta ubicaciones en lenguaje natural  
✅ **Clasificación de severidad** - Prioriza alertas según urgencia (1-10)  
✅ **Detección mejorada de falsos positivos** - Reduce alertas irrelevantes  
✅ **Resúmenes inteligentes** - Notificaciones más informativas  

**Importante**: Toda la funcionalidad original se mantiene intacta. El sistema puede funcionar con o sin IA.

---

## 🆕 Archivos Nuevos

### 1. `ai_analyzer.py`
**Módulo principal de análisis con IA**

Funciones principales:
- `analyze_news()`: Análisis completo de una noticia
- `extract_location_ai()`: Extracción inteligente de ubicación
- `classify_severity()`: Clasificación de severidad (1-10)
- `generate_summary()`: Generación de resúmenes
- `validate_relevance()`: Validación de relevancia

### 2. `main_ai.py`
**Script principal mejorado con IA**

Características:
- Integración completa con OpenAI
- Fallback a método tradicional si IA falla
- Pre-filtrado rápido antes de análisis IA
- Procesamiento optimizado para reducir costos

### 3. `notifier_ai.py`
**Notificador mejorado con información de IA**

Mejoras en notificaciones:
- Muestra nivel de severidad (CRÍTICA/GRAVE/MODERADA/MENOR)
- Indica número de víctimas/heridos
- Reporta impacto en tráfico (ALTO/MEDIO/BAJO)
- Señala presencia de servicios de emergencia
- Emojis dinámicos según severidad

### 4. `run_scheduled_ai.py`
**Script de ejecución programada con IA**

Ejecuta el sistema mejorado cada 30 minutos en horarios fijos (:00 y :30)

---

## 🚀 Cómo Usar el Sistema Mejorado

### Opción 1: Ejecución Manual Única

```bash
cd /home/ubuntu/news_monitor_app

# Configurar credenciales
export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
export TELEGRAM_CHAT_ID="7510716093"

# Ejecutar con IA
python3.11 main_ai.py
```

### Opción 2: Ejecución Automática (Horarios Fijos)

```bash
cd /home/ubuntu/news_monitor_app

# Ejecutar en background con nohup
nohup bash -c 'export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0" && export TELEGRAM_CHAT_ID="7510716093" && python3.11 -u run_scheduled_ai.py' > monitor_ai.log 2>&1 &

# Ver el log en tiempo real
tail -f monitor_ai.log
```

### Opción 3: Usar Sistema Original (Sin IA)

El sistema original sigue funcionando sin cambios:

```bash
python3.11 main.py
```

---

## 🎯 Análisis con IA - Detalles Técnicos

### Modelo Utilizado

**Modelo**: `gpt-4o-mini`
- Más económico que GPT-4 (~90% más barato)
- Más rápido (~2x velocidad)
- Excelente para tareas de análisis estructurado
- Costo aproximado: ~$0.001-0.003 USD por noticia

**Alternativas**:
- `gpt-4o`: Más preciso pero más caro
- `gpt-3.5-turbo`: Más económico pero menos preciso

### Flujo de Análisis

```
1. Scraping de noticias
   ↓
2. Pre-filtrado con palabras clave (rápido, sin IA)
   ↓
3. Solo candidatos relevantes → Análisis con IA
   ├─ Validar relevancia
   ├─ Clasificar categoría
   ├─ Extraer ubicación precisa
   ├─ Calcular severidad (1-10)
   ├─ Contar víctimas
   ├─ Evaluar impacto en tráfico
   └─ Generar resumen
   ↓
4. Geocodificación (sin cambios)
   ↓
5. Verificación de radio (sin cambios)
   ↓
6. Notificación mejorada con datos de IA
```

### Respuesta de IA (Formato JSON)

```json
{
  "is_relevant": true,
  "category": "accidente_vial",
  "severity": 7,
  "location": {
    "extracted": "Av. Lázaro Cárdenas altura Fundadores",
    "normalized": "Lázaro Cárdenas, San Pedro Garza García, NL",
    "confidence": 0.95,
    "is_specific": true
  },
  "summary": "Choque múltiple deja 3 heridos en Valle Oriente",
  "details": {
    "victims": 3,
    "traffic_impact": "high",
    "emergency_services": true,
    "time_reference": "current"
  },
  "exclusion_reason": null
}
```

---

## 📊 Clasificación de Severidad

### Escala 1-10

**1-3: MENOR** ℹ️
- Sin heridos
- Daños materiales leves
- Impacto mínimo en tráfico
- Ejemplo: Choque leve sin lesionados

**4-6: MODERADA** ⚠️
- Heridos leves
- Tráfico afectado
- Servicios de emergencia presentes
- Ejemplo: Accidente con heridos leves

**7-8: GRAVE** 🚨
- Heridos graves
- Múltiples vehículos involucrados
- Cierre de vialidad
- Ejemplo: Choque múltiple con heridos graves

**9-10: CRÍTICA** 🚨🚨
- Víctimas fatales
- Peligro inminente
- Emergencia mayor
- Ejemplo: Balacera con víctimas fatales

---

## 📱 Formato de Notificaciones Mejoradas

### Ejemplo de Alerta con IA

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
    Servicios de emergencia en el lugar.

📡 Milenio Monterrey
🔗 [Ver noticia completa]

⏰ 28/10/2025 18:00
```

### Comparación: Sin IA vs Con IA

**Sin IA (Original)**:
```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Choque en Lázaro Cárdenas deja 3 heridos

📏 A 2.1 km de Costco Valle Oriente
🗺️ Lázaro Cárdenas

📡 Milenio Monterrey
🔗 [Ver noticia completa]

⏰ 28/10/2025 18:00
```

**Con IA (Mejorado)**:
- ✅ Severidad clasificada (7/10 - GRAVE)
- ✅ Número de víctimas (3)
- ✅ Impacto en tráfico (ALTO)
- ✅ Servicios de emergencia (Sí)
- ✅ Ubicación más precisa
- ✅ Resumen inteligente

---

## 💰 Costos Estimados

### Análisis de Costos con OpenAI

**Escenario típico**:
- 30 noticias analizadas por monitoreo
- 2-3 candidatas pasan pre-filtro
- Solo 2-3 análisis con IA por monitoreo
- 48 monitoreos al día (cada 30 min)

**Cálculo diario**:
- ~100-150 análisis con IA por día
- ~$0.15-0.45 USD por día
- ~$4.50-13.50 USD por mes

**Optimizaciones implementadas**:
1. Pre-filtrado sin IA (reduce 90% de llamadas)
2. Modelo económico (gpt-4o-mini)
3. Límite de tokens (max 1000 por análisis)
4. Temperatura baja (respuestas consistentes)

---

## 🔧 Configuración Avanzada

### Cambiar Modelo de IA

Editar `ai_analyzer.py`:

```python
# Para mayor precisión (más caro)
analyzer = AINewsAnalyzer(model="gpt-4o")

# Para mayor economía (menos preciso)
analyzer = AINewsAnalyzer(model="gpt-3.5-turbo")

# Recomendado (balance)
analyzer = AINewsAnalyzer(model="gpt-4o-mini")
```

### Desactivar IA Temporalmente

En `main_ai.py`:

```python
# Usar sin IA (método tradicional)
monitor = NewsMonitorAI(use_ai=False)
```

### Ajustar Parámetros de IA

En `ai_analyzer.py`:

```python
def __init__(self, model: str = "gpt-4o-mini"):
    self.model = model
    self.max_tokens = 1000        # Aumentar para análisis más detallados
    self.temperature = 0.1        # 0 = determinista, 1 = creativo
```

---

## 🧪 Pruebas y Validación

### Probar Módulo de IA

```bash
cd /home/ubuntu/news_monitor_app
python3.11 ai_analyzer.py
```

### Probar Notificador Mejorado

```bash
cd /home/ubuntu/news_monitor_app
python3.11 notifier_ai.py
```

### Probar Sistema Completo

```bash
cd /home/ubuntu/news_monitor_app
export TELEGRAM_BOT_TOKEN="TU_TOKEN"
export TELEGRAM_CHAT_ID="TU_CHAT_ID"
python3.11 main_ai.py
```

---

## 📈 Ventajas del Sistema Mejorado

### 1. Mayor Precisión
- **Antes**: Regex básico para palabras clave
- **Ahora**: Comprensión de contexto y semántica
- **Resultado**: Menos falsos positivos

### 2. Mejor Extracción de Ubicaciones
- **Antes**: Patrones regex limitados
- **Ahora**: Detección en lenguaje natural
- **Resultado**: Más ubicaciones detectadas correctamente

### 3. Priorización de Alertas
- **Antes**: Todas las alertas iguales
- **Ahora**: Severidad clasificada (1-10)
- **Resultado**: Respuesta proporcional a la urgencia

### 4. Información Más Rica
- **Antes**: Solo título y ubicación
- **Ahora**: Víctimas, impacto, servicios de emergencia
- **Resultado**: Mejor toma de decisiones

### 5. Resúmenes Inteligentes
- **Antes**: Primeros 300 caracteres
- **Ahora**: Resumen generado por IA
- **Resultado**: Información más relevante

---

## 🔍 Comparación de Resultados

### Caso de Prueba Real

**Noticia**: "Choque en Lázaro Cárdenas a la altura de Fundadores deja 3 heridos. Protección Civil y Cruz Roja en el lugar."

#### Análisis Tradicional:
```
✓ Detectado: Sí (palabra "choque")
✓ Categoría: Accidente Vial
✓ Ubicación: "lázaro cárdenas" (genérica)
✗ Severidad: No clasificada
✗ Víctimas: No detectadas
✗ Impacto: No evaluado
```

#### Análisis con IA:
```
✓ Detectado: Sí
✓ Categoría: Accidente Vial
✓ Ubicación: "Av. Lázaro Cárdenas altura Fundadores" (específica)
✓ Severidad: 7/10 (GRAVE)
✓ Víctimas: 3 heridos
✓ Impacto en tráfico: ALTO
✓ Servicios de emergencia: Sí
✓ Confianza: 0.95
```

---

## 🛡️ Manejo de Errores

### Fallback Automático

Si el análisis con IA falla, el sistema automáticamente usa el método tradicional:

```python
ai_result = self.ai_analyzer.analyze_news(titulo, content)

if not ai_result:
    print(f"   ⚠️  Error en análisis IA, usando método tradicional")
    return self.process_news_item_traditional(news_item)
```

### Timeouts y Reintentos

- Timeout de API: 10 segundos
- En caso de error: continúa con siguiente noticia
- No detiene el monitoreo completo

---

## 📝 Logs y Monitoreo

### Ver Logs del Sistema con IA

```bash
# Log en tiempo real
tail -f /home/ubuntu/news_monitor_app/monitor_ai.log

# Últimas 100 líneas
tail -100 /home/ubuntu/news_monitor_app/monitor_ai.log

# Buscar errores
grep "Error" /home/ubuntu/news_monitor_app/monitor_ai.log
```

### Verificar Proceso Activo

```bash
# Ver si está corriendo
ps aux | grep run_scheduled_ai | grep -v grep

# Ver uso de recursos
top -p $(pgrep -f run_scheduled_ai)
```

### Detener Sistema

```bash
# Detener proceso
killall -9 python3.11

# O específicamente
pkill -f run_scheduled_ai
```

---

## 🔄 Migración desde Sistema Original

### Paso 1: Backup
```bash
cp /home/ubuntu/news_monitor_app/processed_news.txt /home/ubuntu/news_monitor_app/processed_news.txt.backup
```

### Paso 2: Detener Sistema Original
```bash
killall -9 python3.11
```

### Paso 3: Iniciar Sistema Mejorado
```bash
cd /home/ubuntu/news_monitor_app
nohup bash -c 'export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0" && export TELEGRAM_CHAT_ID="7510716093" && python3.11 -u run_scheduled_ai.py' > monitor_ai.log 2>&1 &
```

### Paso 4: Verificar
```bash
tail -f monitor_ai.log
```

---

## 🎓 Mejores Prácticas

### 1. Monitoreo de Costos
- Revisar uso de API en OpenAI Dashboard
- Establecer límites de gasto mensuales
- Monitorear número de llamadas por día

### 2. Optimización
- Mantener pre-filtrado activo
- Usar modelo económico (gpt-4o-mini)
- Limitar tokens por análisis

### 3. Mantenimiento
- Revisar logs diariamente
- Verificar precisión de alertas
- Ajustar prompts según resultados

### 4. Backup
- Respaldar `processed_news.txt` semanalmente
- Guardar logs importantes
- Documentar cambios en configuración

---

## 🆘 Solución de Problemas

### Problema: "ModuleNotFoundError: No module named 'openai'"
**Solución**:
```bash
pip3 install openai
```

### Problema: "Error en análisis con IA"
**Causa**: API key no configurada o inválida
**Solución**:
```bash
# Verificar que OPENAI_API_KEY está configurado
echo $OPENAI_API_KEY

# Si no está, el sistema usa las credenciales del entorno Manus
```

### Problema: Costos muy altos
**Solución**:
1. Verificar que pre-filtrado está activo
2. Cambiar a modelo más económico
3. Reducir `max_tokens`
4. Aumentar intervalo de monitoreo

### Problema: Análisis muy lento
**Solución**:
1. Usar modelo más rápido (gpt-4o-mini)
2. Reducir `max_tokens`
3. Verificar conexión a internet

---

## 📚 Recursos Adicionales

### Documentación de OpenAI
- API Reference: https://platform.openai.com/docs/
- Pricing: https://openai.com/pricing
- Best Practices: https://platform.openai.com/docs/guides/production-best-practices

### Archivos Relacionados
- `DOCUMENTO_COMPLETO_PROYECTO.md`: Documentación del sistema original
- `README.md`: Guía general del proyecto
- `INICIO_RAPIDO.md`: Guía de inicio rápido

---

## ✅ Checklist de Implementación

- [x] Módulo de IA creado (`ai_analyzer.py`)
- [x] Script principal mejorado (`main_ai.py`)
- [x] Notificador mejorado (`notifier_ai.py`)
- [x] Script programado con IA (`run_scheduled_ai.py`)
- [x] Pruebas de módulo de IA
- [x] Pruebas de notificador
- [x] Prueba completa end-to-end
- [x] Documentación completa
- [x] Compatibilidad con sistema original

---

## 🎉 Conclusión

El sistema de monitoreo ha sido exitosamente mejorado con **Inteligencia Artificial** manteniendo toda la funcionalidad original. Las mejoras proporcionan:

- ✅ **Mayor precisión** en detección de eventos
- ✅ **Mejor extracción** de ubicaciones
- ✅ **Clasificación de severidad** para priorización
- ✅ **Información más rica** en notificaciones
- ✅ **Reducción de falsos positivos**

El sistema está listo para producción y puede ser desplegado en cualquier servidor con acceso a OpenAI API.

---

**Fecha de implementación**: 28 de octubre de 2025  
**Versión**: 2.0 - Sistema con IA  
**Powered by**: OpenAI GPT-4o-mini
