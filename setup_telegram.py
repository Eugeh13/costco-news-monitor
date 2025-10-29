"""
Script interactivo para configurar Telegram Bot.
"""

import requests
import os


def print_header():
    """Imprime el encabezado."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Configuración de Telegram Bot                                  ║
║   Sistema de Monitoreo Costco MTY                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)


def print_instructions():
    """Imprime las instrucciones paso a paso."""
    print("""
📱 PASO 1: Crear tu Bot de Telegram (2 minutos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Abre Telegram en tu celular
2. Busca: @BotFather (es el bot oficial de Telegram)
3. Inicia una conversación con él
4. Envía el comando: /newbot
5. BotFather te pedirá:
   - Un NOMBRE para tu bot (ej: "Monitor Costco MTY")
   - Un USERNAME para tu bot (debe terminar en 'bot', ej: "costco_mty_bot")
6. BotFather te dará un TOKEN (algo como: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
7. COPIA ese token

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def get_bot_token():
    """Solicita el token del bot."""
    print("\n🔑 Ingresa el TOKEN que te dio BotFather:")
    print("   (Se ve algo así: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)")
    token = input("\nTOKEN: ").strip()
    return token


def verify_token(token):
    """Verifica que el token sea válido."""
    print("\n⏳ Verificando token...")
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"\n✓ Token válido!")
                print(f"✓ Nombre del bot: {bot_info.get('first_name')}")
                print(f"✓ Username: @{bot_info.get('username')}")
                return True
        
        print(f"\n❌ Token inválido. Error: {response.text}")
        return False
        
    except Exception as e:
        print(f"\n❌ Error verificando token: {e}")
        return False


def print_chat_id_instructions(bot_username):
    """Imprime las instrucciones para obtener el Chat ID."""
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 PASO 2: Obtener tu Chat ID (1 minuto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. En Telegram, busca tu bot: @{bot_username}
2. Inicia una conversación con él
3. Envía cualquier mensaje (ej: "Hola")
4. Vuelve aquí y presiona ENTER

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def get_chat_id(token):
    """Obtiene el Chat ID del usuario."""
    input("\nPresiona ENTER cuando hayas enviado un mensaje a tu bot...")
    
    print("\n⏳ Buscando tu Chat ID...")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                updates = data.get('result', [])
                
                if not updates:
                    print("\n❌ No se encontraron mensajes.")
                    print("   Asegúrate de haber enviado un mensaje a tu bot.")
                    return None
                
                # Obtener el último mensaje
                last_update = updates[-1]
                chat_id = last_update.get('message', {}).get('chat', {}).get('id')
                
                if chat_id:
                    print(f"\n✓ Chat ID encontrado: {chat_id}")
                    return str(chat_id)
                else:
                    print("\n❌ No se pudo obtener el Chat ID.")
                    return None
        
        print(f"\n❌ Error obteniendo Chat ID: {response.text}")
        return None
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def send_test_message(token, chat_id):
    """Envía un mensaje de prueba."""
    print("\n⏳ Enviando mensaje de prueba...")
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        message = """🚨 <b>PRUEBA - Sistema Configurado Correctamente</b>

✓ Tu bot está funcionando perfectamente!
✓ Recibirás notificaciones de alto impacto aquí
✓ Radio: 5 km alrededor de Costcos en Monterrey

📍 Sucursales monitoreadas:
• Costco Carretera Nacional
• Costco Cumbres  
• Costco Valle Oriente

⏱️ Intervalo: Cada 30 minutos

¡Todo listo para empezar! 🎉"""
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("\n✓ Mensaje de prueba enviado!")
            print("✓ Revisa tu Telegram, deberías haber recibido un mensaje")
            return True
        else:
            print(f"\n❌ Error enviando mensaje: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def save_credentials(token, chat_id):
    """Guarda las credenciales en variables de entorno."""
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("💾 GUARDAR CREDENCIALES")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    print("\nPara que el sistema funcione, necesitas configurar estas variables:")
    print(f"\nexport TELEGRAM_BOT_TOKEN=\"{token}\"")
    print(f"export TELEGRAM_CHAT_ID=\"{chat_id}\"")
    
    # Intentar guardar en el entorno actual
    os.environ['TELEGRAM_BOT_TOKEN'] = token
    os.environ['TELEGRAM_CHAT_ID'] = chat_id
    
    print("\n✓ Variables configuradas para esta sesión")
    
    print("\n📝 Para hacerlas permanentes, agrega estas líneas a tu ~/.bashrc:")
    print(f"\necho 'export TELEGRAM_BOT_TOKEN=\"{token}\"' >> ~/.bashrc")
    print(f"echo 'export TELEGRAM_CHAT_ID=\"{chat_id}\"' >> ~/.bashrc")
    print("source ~/.bashrc")


def main():
    """Función principal."""
    print_header()
    print_instructions()
    
    # Paso 1: Obtener y verificar token
    while True:
        token = get_bot_token()
        if verify_token(token):
            break
        print("\n❌ Intenta de nuevo con el token correcto.")
    
    # Obtener el username del bot
    url = f"https://api.telegram.org/bot{token}/getMe"
    response = requests.get(url)
    bot_username = response.json().get('result', {}).get('username', 'tu_bot')
    
    # Paso 2: Obtener Chat ID
    print_chat_id_instructions(bot_username)
    
    chat_id = None
    while not chat_id:
        chat_id = get_chat_id(token)
        if not chat_id:
            retry = input("\n¿Quieres intentar de nuevo? (s/n): ")
            if retry.lower() != 's':
                print("\n❌ Configuración cancelada.")
                return
    
    # Paso 3: Enviar mensaje de prueba
    send_test_message(token, chat_id)
    
    # Paso 4: Guardar credenciales
    save_credentials(token, chat_id)
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🎉 ¡CONFIGURACIÓN COMPLETADA!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("\nYa puedes ejecutar el sistema:")
    print("  python run_30min.py")
    print("\nRecibirás notificaciones en Telegram cada vez que ocurra")
    print("un evento de alto impacto cerca de los Costcos en Monterrey.")
    print("\n¡Disfruta de tu sistema de alertas! 🚀")


if __name__ == "__main__":
    main()

