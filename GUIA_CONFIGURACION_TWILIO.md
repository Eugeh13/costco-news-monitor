# Guía de Configuración de Twilio para SMS

Esta guía te ayudará a configurar Twilio para recibir notificaciones SMS en tu celular.

## ¿Qué es Twilio?

Twilio es un servicio de comunicaciones que permite enviar SMS y mensajes de WhatsApp de forma programática. Ofrece una **cuenta gratuita de prueba** con crédito inicial para enviar mensajes.

## Paso 1: Crear Cuenta en Twilio (GRATIS)

1. **Visita**: https://www.twilio.com/try-twilio
2. **Regístrate** con tu email y crea una contraseña
3. **Verifica tu email** haciendo clic en el enlace que te enviarán
4. **Verifica tu número de teléfono**: +52 8124686732
   - Recibirás un código de verificación por SMS
   - Ingresa el código en el sitio web

## Paso 2: Obtener Credenciales

Una vez dentro de tu cuenta Twilio:

1. **Ve al Dashboard**: https://console.twilio.com/
2. **Busca estas credenciales**:
   - **Account SID**: Algo como `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: Haz clic en "Show" para verlo

3. **Copia estas credenciales** (las necesitarás después)

## Paso 3: Obtener un Número de Teléfono Twilio

### Opción A: Cuenta de Prueba (GRATIS)

Con la cuenta de prueba, Twilio te asigna un número automáticamente:

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Verás un número como: `+1 555 123 4567`
3. **Copia este número** (es tu `SMS_FROM_NUMBER`)

**Limitaciones de la cuenta de prueba:**
- Solo puedes enviar SMS a números verificados
- Los mensajes incluyen un prefijo de Twilio
- Crédito limitado (~$15 USD)

### Opción B: Cuenta de Pago (Recomendado para producción)

Si quieres usar el servicio sin limitaciones:

1. **Agregar saldo**: Mínimo $20 USD
2. **Comprar un número mexicano**: ~$1 USD/mes
3. **Costo por SMS**: ~$0.0075 USD por mensaje

## Paso 4: Configurar Variables de Entorno

Ahora necesitas configurar las credenciales en tu sistema:

### En Linux/Mac:

```bash
export TWILIO_ACCOUNT_SID="tu_account_sid_aqui"
export TWILIO_AUTH_TOKEN="tu_auth_token_aqui"
```

Para que sean permanentes, agrégalas a tu archivo `~/.bashrc` o `~/.zshrc`:

```bash
echo 'export TWILIO_ACCOUNT_SID="tu_account_sid_aqui"' >> ~/.bashrc
echo 'export TWILIO_AUTH_TOKEN="tu_auth_token_aqui"' >> ~/.bashrc
source ~/.bashrc
```

### En Windows (CMD):

```cmd
setx TWILIO_ACCOUNT_SID "tu_account_sid_aqui"
setx TWILIO_AUTH_TOKEN "tu_auth_token_aqui"
```

### En Windows (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable("TWILIO_ACCOUNT_SID", "tu_account_sid_aqui", "User")
[Environment]::SetEnvironmentVariable("TWILIO_AUTH_TOKEN", "tu_auth_token_aqui", "User")
```

## Paso 5: Actualizar config.py

Edita el archivo `config.py` y actualiza el número de Twilio:

```python
SMS_FROM_NUMBER = "+15551234567"  # Reemplaza con tu número de Twilio
```

## Paso 6: Instalar Dependencias

```bash
cd news_monitor_app
pip install -r requirements.txt
```

Esto instalará:
- requests
- beautifulsoup4
- geopy
- twilio

## Paso 7: Probar el Sistema

### Prueba Rápida

Crea un archivo `test_sms.py`:

```python
import os
from twilio.rest import Client

# Credenciales
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')

# Números
from_number = "+15551234567"  # Tu número Twilio
to_number = "+528124686732"   # Tu celular

# Crear cliente
client = Client(account_sid, auth_token)

# Enviar mensaje de prueba
message = client.messages.create(
    body="🚨 Prueba del sistema de monitoreo Costco MTY",
    from_=from_number,
    to=to_number
)

print(f"✓ SMS enviado correctamente (SID: {message.sid})")
```

Ejecuta:
```bash
python test_sms.py
```

Si recibes el SMS, ¡todo está funcionando correctamente! 🎉

## Paso 8: Ejecutar el Monitoreo

### Ejecución Continua (cada 30 minutos)

```bash
python run_30min.py
```

Este script:
- Monitorea noticias cada 30 minutos
- Te envía SMS cuando detecta eventos de alto impacto cerca de Costco
- Funciona 24/7 mientras esté ejecutándose

### Ejecutar en Segundo Plano (Linux/Mac)

```bash
nohup python run_30min.py > monitor.log 2>&1 &
```

Para detenerlo:
```bash
ps aux | grep run_30min.py
kill [PID]
```

### Ejecutar como Servicio (Linux con systemd)

Crea `/etc/systemd/system/news-monitor.service`:

```ini
[Unit]
Description=News Monitor Costco MTY
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/news_monitor_app
Environment="TWILIO_ACCOUNT_SID=tu_account_sid"
Environment="TWILIO_AUTH_TOKEN=tu_auth_token"
ExecStart=/usr/bin/python3 run_30min.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl enable news-monitor
sudo systemctl start news-monitor
sudo systemctl status news-monitor
```

## Ejemplo de SMS que Recibirás

```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Fuerte choque en Av. Gonzalitos deja varios heridos

📏 A 3.2 km de Costco Cumbres
🗺️ Av. Gonzalitos con Av. Madero

📡 Milenio Monterrey
🔗 https://www.milenio.com/...
```

## Costos Estimados

### Cuenta de Prueba (GRATIS)
- $15 USD de crédito inicial
- ~2000 SMS gratis
- Solo a números verificados

### Cuenta de Pago
- **Número mexicano**: ~$1 USD/mes
- **SMS saliente**: ~$0.0075 USD por mensaje
- **Costo mensual estimado** (1 SMS cada 30 min durante 1 mes):
  - 2 SMS/hora × 24 horas × 30 días = 1,440 SMS
  - 1,440 × $0.0075 = ~$10.80 USD/mes
  - Total: ~$12 USD/mes (número + SMS)

## Solución de Problemas

### Error: "Unable to create record: The number is unverified"

**Solución**: Con cuenta de prueba, debes verificar tu número:
1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Haz clic en "Add a new number"
3. Ingresa +528124686732 y verifica

### Error: "Authentication failed"

**Solución**: Verifica que las variables de entorno estén configuradas:
```bash
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN
```

### No recibo SMS

**Verificar**:
1. Que el número de destino sea correcto: +528124686732
2. Que el número de origen sea tu número Twilio
3. Que tengas crédito en tu cuenta Twilio
4. Revisa los logs en: https://console.twilio.com/us1/monitor/logs/sms

## Alternativas Gratuitas

Si prefieres no usar Twilio, hay otras opciones:

### 1. Telegram Bot (GRATIS)
- Crea un bot con @BotFather
- Envía mensajes ilimitados gratis
- Requiere tener Telegram instalado

### 2. Email (GRATIS)
- Usa Gmail SMTP
- Envía a tu email
- Configura notificaciones push en tu celular

### 3. Discord Webhook (GRATIS)
- Crea un servidor de Discord
- Configura un webhook
- Recibe notificaciones en Discord

## Soporte

Si tienes problemas:
1. Revisa la documentación de Twilio: https://www.twilio.com/docs/sms
2. Consulta los logs del sistema
3. Verifica las credenciales y números

---

**¡Listo!** Una vez configurado, recibirás alertas automáticas en tu celular cada vez que ocurra un evento de alto impacto cerca de las sucursales de Costco en Monterrey.

