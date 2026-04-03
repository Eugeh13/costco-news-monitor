# 🚀 Inicio Rápido - Sistema de Monitoreo Costco MTY

## Tu Configuración

- **📱 Número de celular**: +52 8124686732
- **⏱️ Intervalo**: 30 minutos
- **📍 Radio**: 5 km alrededor de 3 Costcos en Monterrey

## Pasos para Activar las Notificaciones SMS

### 1️⃣ Crear Cuenta en Twilio (5 minutos)

**Twilio te da $15 USD GRATIS para empezar** (~2000 SMS)

1. Ve a: https://www.twilio.com/try-twilio
2. Regístrate con tu email
3. Verifica tu email
4. **IMPORTANTE**: Verifica tu número +528124686732
   - Recibirás un código por SMS
   - Ingrésalo en el sitio

### 2️⃣ Obtener Credenciales (2 minutos)

1. Ve al Dashboard: https://console.twilio.com/
2. Copia estos datos:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: Haz clic en "Show" para verlo

### 3️⃣ Obtener Número de Teléfono (1 minuto)

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Verás un número asignado automáticamente: `+1 555 123 4567`
3. **Cópialo** (lo necesitarás en el siguiente paso)

### 4️⃣ Configurar el Sistema (3 minutos)

#### A) Configurar Variables de Entorno

**Linux/Mac:**
```bash
export TWILIO_ACCOUNT_SID="tu_account_sid_aqui"
export TWILIO_AUTH_TOKEN="tu_auth_token_aqui"
```

**Windows (CMD):**
```cmd
setx TWILIO_ACCOUNT_SID "tu_account_sid_aqui"
setx TWILIO_AUTH_TOKEN "tu_auth_token_aqui"
```

#### B) Editar config.py

Abre el archivo `config.py` y actualiza esta línea:

```python
SMS_FROM_NUMBER = "+15551234567"  # ← Reemplaza con tu número de Twilio
```

### 5️⃣ Instalar Dependencias (2 minutos)

```bash
cd news_monitor_app
pip install -r requirements.txt
```

### 6️⃣ Probar la Configuración (1 minuto)

```bash
python test_twilio.py
```

Este script:
- ✓ Verifica tus credenciales
- ✓ Prueba la conexión con Twilio
- ✓ Te permite enviar un SMS de prueba

Si recibes el SMS de prueba, **¡todo está listo!** 🎉

### 7️⃣ Ejecutar el Monitoreo

```bash
python run_30min.py
```

**¡Listo!** Ahora recibirás alertas cada vez que ocurra algo importante cerca de los Costcos.

---

## 📱 Ejemplo de SMS que Recibirás

```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Fuerte choque en Av. Gonzalitos 
deja varios heridos

📏 A 3.2 km de Costco Cumbres
🗺️ Av. Gonzalitos con Av. Madero

📡 Milenio Monterrey
🔗 https://milenio.com/...
```

---

## ⚙️ Opciones de Ejecución

### Opción 1: Ejecutar Manualmente

```bash
python run_30min.py
```

- Monitorea cada 30 minutos
- Debes mantener la terminal abierta
- Presiona Ctrl+C para detener

### Opción 2: Ejecutar en Segundo Plano (Linux/Mac)

```bash
nohup python run_30min.py > monitor.log 2>&1 &
```

- Funciona aunque cierres la terminal
- Los logs se guardan en `monitor.log`

Para detenerlo:
```bash
ps aux | grep run_30min
kill [PID]
```

### Opción 3: Ejecutar con Cron (Automático)

Edita tu crontab:
```bash
crontab -e
```

Agrega esta línea:
```
*/30 * * * * cd /ruta/a/news_monitor_app && python3 run_30min.py >> monitor.log 2>&1
```

---

## 💰 Costos

### Cuenta de Prueba (GRATIS)
- $15 USD de crédito inicial
- ~2000 SMS gratis
- Solo puedes enviar a números verificados

### Cuenta de Pago (Opcional)
- **Número mexicano**: ~$1 USD/mes
- **SMS**: ~$0.0075 USD por mensaje
- **Costo estimado**: ~$12 USD/mes (si recibes ~1440 SMS/mes)

---

## 🆘 Solución de Problemas

### "The number is unverified"

**Solución**: Verifica tu número en Twilio:
1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Agrega +528124686732
3. Verifica con el código que recibirás

### "Authentication failed"

**Solución**: Verifica las variables de entorno:
```bash
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
```

Si están vacías, configúralas de nuevo.

### No recibo SMS

**Verifica**:
1. Que tu número esté verificado en Twilio
2. Que el `SMS_FROM_NUMBER` en `config.py` sea correcto
3. Que tengas crédito en tu cuenta Twilio
4. Revisa los logs en: https://console.twilio.com/us1/monitor/logs/sms

---

## 📞 Soporte

Si tienes problemas:
1. Lee la guía completa: `GUIA_CONFIGURACION_TWILIO.md`
2. Ejecuta el test: `python test_twilio.py`
3. Revisa los logs del sistema

---

## 🎯 ¿Qué Detecta el Sistema?

El sistema te alertará sobre:

- ✅ **Accidentes viales graves** (choques, volcaduras, atropellos)
- ✅ **Incendios** (comercios, casas, edificios)
- ✅ **Situaciones de seguridad** (balaceras, operativos, persecuciones)
- ✅ **Bloqueos de vialidades** (manifestaciones, cierres)
- ✅ **Desastres naturales** (inundaciones, deslaves, tormentas)

**Solo si ocurren dentro de 5 km de:**
- Costco Carretera Nacional
- Costco Cumbres
- Costco Valle Oriente

---

**¡Disfruta de tu sistema de alertas personalizado!** 🚀

