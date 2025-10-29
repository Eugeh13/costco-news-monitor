# 🚀 Inicio Rápido - Sistema con IA

## Sistema de Monitoreo de Noticias Costco Monterrey
### Versión Mejorada con OpenAI

---

## ⚡ Ejecución Inmediata

### Opción 1: Prueba Rápida (Una Vez)

```bash
cd /home/ubuntu/news_monitor_app

export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
export TELEGRAM_CHAT_ID="7510716093"

python3.11 main_ai.py
```

### Opción 2: Modo Automático (Cada 30 minutos)

```bash
cd /home/ubuntu/news_monitor_app

nohup bash -c 'export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0" && export TELEGRAM_CHAT_ID="7510716093" && python3.11 -u run_scheduled_ai.py' > monitor_ai.log 2>&1 &

# Ver el log
tail -f monitor_ai.log
```

---

## 📋 Comandos Útiles

### Verificar Estado
```bash
# Ver si está corriendo
ps aux | grep run_scheduled_ai | grep -v grep

# Ver log en tiempo real
tail -f /home/ubuntu/news_monitor_app/monitor_ai.log

# Ver últimas 50 líneas
tail -50 /home/ubuntu/news_monitor_app/monitor_ai.log
```

### Detener Sistema
```bash
killall -9 python3.11
```

### Reiniciar Sistema
```bash
# Detener
killall -9 python3.11

# Iniciar
cd /home/ubuntu/news_monitor_app
nohup bash -c 'export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0" && export TELEGRAM_CHAT_ID="7510716093" && python3.11 -u run_scheduled_ai.py' > monitor_ai.log 2>&1 &
```

---

## 🧪 Pruebas Rápidas

### Probar Análisis de IA
```bash
cd /home/ubuntu/news_monitor_app
python3.11 ai_analyzer.py
```

### Probar Notificaciones
```bash
cd /home/ubuntu/news_monitor_app
export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
export TELEGRAM_CHAT_ID="7510716093"
python3.11 notifier_ai.py test
```

---

## 📊 Qué Esperar

### Primera Ejecución
```
✓ Sistema inicializado con análisis de IA (OpenAI)
🔍 Iniciando monitoreo
🤖 Modo: Análisis con IA (OpenAI)

Monitoreando: Milenio Última Hora...
  → 10 noticias encontradas
  
Monitoreando: Milenio Monterrey...
  → 17 noticias encontradas
  
✓ Monitoreo completado - 30 noticias analizadas
✓ Alertas enviadas: 0
✓ Resumen enviado a Telegram
```

### Cuando Detecta Evento
```
📰 Candidata detectada: Choque en Lázaro Cárdenas...
   🤖 Analizando con IA...
   ✓ Relevante - Categoría: accidente_vial
   ⚡ Severidad: 7/10
   📍 Ubicación: Av. Lázaro Cárdenas altura Fundadores
   🗺️  Coordenadas: 25.639695, -100.317631
   ✓ Dentro del radio: 2.1 km de Costco Valle Oriente
   
✓ Notificación enviada a Telegram
```

---

## 🆚 Diferencias Clave

### Sistema Original (`main.py`)
- ✅ Rápido
- ✅ Sin costos
- ⚠️ Menos preciso
- ⚠️ Sin clasificación de severidad

### Sistema con IA (`main_ai.py`)
- ✅ Muy preciso
- ✅ Clasifica severidad
- ✅ Detecta víctimas
- ✅ Evalúa impacto en tráfico
- ⚠️ Costo: ~$5-15 USD/mes

---

## 💡 Tips

### 1. Monitorear Logs
```bash
# Ver errores
grep "Error" monitor_ai.log

# Ver alertas enviadas
grep "ALERTA" monitor_ai.log

# Ver análisis con IA
grep "Analizando con IA" monitor_ai.log
```

### 2. Verificar Costos
- Dashboard de OpenAI: https://platform.openai.com/usage
- Revisar semanalmente
- Costo esperado: ~$0.15-0.45 USD por día

### 3. Optimizar Rendimiento
- Pre-filtrado reduce 90% de llamadas a IA
- Solo analiza candidatos relevantes
- Modelo económico (gpt-4o-mini)

---

## 🔧 Configuración Rápida

### Cambiar Intervalo de Monitoreo

Editar `run_scheduled_ai.py`:
```python
# Cambiar de 30 a 60 minutos
# Modificar la función get_next_scheduled_time()
```

### Desactivar IA Temporalmente

En `main_ai.py`:
```python
# Línea 30
monitor = NewsMonitorAI(use_ai=False)  # Cambiar True a False
```

### Cambiar Modelo de IA

En `ai_analyzer.py`:
```python
# Línea 18
def __init__(self, model: str = "gpt-4o-mini"):  # Cambiar modelo aquí
```

---

## 📱 Notificaciones en Telegram

### Resumen (Sin alertas)
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

### Alerta (Con evento)
```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Choque múltiple en Lázaro Cárdenas

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

## 🆘 Problemas Comunes

### "ModuleNotFoundError"
```bash
pip3 install -r requirements.txt
```

### "No se envían notificaciones"
```bash
# Verificar credenciales
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# Probar notificador
python3.11 notifier_ai.py test
```

### "Error en análisis con IA"
- Verificar conexión a internet
- OpenAI API key está configurado automáticamente
- El sistema usa fallback a método tradicional

### "Sistema muy lento"
- Normal: análisis con IA toma 5-10 segundos por noticia
- Solo analiza 2-3 noticias por ciclo (pre-filtradas)
- Tiempo total: ~40-60 segundos por monitoreo

---

## 📚 Documentación Completa

- **GUIA_MEJORAS_IA.md**: Documentación detallada de mejoras
- **README_AI.md**: README completo del sistema
- **DOCUMENTO_COMPLETO_PROYECTO.md**: Documentación original

---

## ✅ Checklist de Inicio

- [ ] Extraer archivos del proyecto
- [ ] Instalar dependencias (`pip3 install -r requirements.txt`)
- [ ] Configurar variables de entorno (TOKEN y CHAT_ID)
- [ ] Probar módulo de IA (`python3.11 ai_analyzer.py`)
- [ ] Probar notificador (`python3.11 notifier_ai.py test`)
- [ ] Ejecutar prueba completa (`python3.11 main_ai.py`)
- [ ] Iniciar modo automático (`run_scheduled_ai.py`)
- [ ] Verificar logs (`tail -f monitor_ai.log`)

---

## 🎯 Próximos Pasos

1. **Ejecutar prueba inicial**
   ```bash
   python3.11 main_ai.py
   ```

2. **Verificar notificación en Telegram**
   - Abrir Telegram
   - Buscar @monitorCostco_bot
   - Verificar mensaje de resumen

3. **Iniciar modo automático**
   ```bash
   nohup bash -c 'export TELEGRAM_BOT_TOKEN="..." && export TELEGRAM_CHAT_ID="..." && python3.11 -u run_scheduled_ai.py' > monitor_ai.log 2>&1 &
   ```

4. **Monitorear durante 24 horas**
   - Revisar logs periódicamente
   - Verificar precisión de alertas
   - Monitorear costos en OpenAI

---

## 🎉 ¡Listo!

El sistema está configurado y listo para usar. Recibirás notificaciones automáticas cada 30 minutos con análisis inteligente de eventos de alto impacto cerca de las sucursales Costco.

**¿Necesitas ayuda?** Consulta la documentación completa en `GUIA_MEJORAS_IA.md`

---

**Versión**: 2.0 con IA  
**Fecha**: Octubre 2025  
**Powered by**: OpenAI GPT-4o-mini
