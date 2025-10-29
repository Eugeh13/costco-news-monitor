"""
Script de prueba para verificar la configuración de Twilio.
"""

import os
import sys


def test_twilio_credentials():
    """Verifica que las credenciales de Twilio estén configuradas."""
    print("="*70)
    print("VERIFICACIÓN DE CREDENCIALES TWILIO")
    print("="*70)
    
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    
    if not account_sid:
        print("❌ TWILIO_ACCOUNT_SID no está configurado")
        print("\nConfigúralo con:")
        print('export TWILIO_ACCOUNT_SID="tu_account_sid"')
        return False
    else:
        print(f"✓ TWILIO_ACCOUNT_SID: {account_sid[:10]}...")
    
    if not auth_token:
        print("❌ TWILIO_AUTH_TOKEN no está configurado")
        print("\nConfigúralo con:")
        print('export TWILIO_AUTH_TOKEN="tu_auth_token"')
        return False
    else:
        print(f"✓ TWILIO_AUTH_TOKEN: {auth_token[:10]}...")
    
    return True


def test_twilio_connection():
    """Prueba la conexión con Twilio."""
    print("\n" + "="*70)
    print("PRUEBA DE CONEXIÓN CON TWILIO")
    print("="*70)
    
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        
        client = Client(account_sid, auth_token)
        
        # Obtener información de la cuenta
        account = client.api.accounts(account_sid).fetch()
        
        print(f"✓ Conexión exitosa")
        print(f"✓ Nombre de cuenta: {account.friendly_name}")
        print(f"✓ Estado: {account.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error conectando con Twilio: {e}")
        return False


def test_send_sms():
    """Envía un SMS de prueba."""
    print("\n" + "="*70)
    print("ENVÍO DE SMS DE PRUEBA")
    print("="*70)
    
    # Importar configuración
    import config
    
    from_number = config.SMS_FROM_NUMBER
    to_number = config.SMS_TO_NUMBER
    
    if not from_number:
        print("❌ SMS_FROM_NUMBER no está configurado en config.py")
        print("\nEdita config.py y agrega tu número de Twilio:")
        print('SMS_FROM_NUMBER = "+15551234567"')
        return False
    
    print(f"De: {from_number}")
    print(f"Para: {to_number}")
    
    respuesta = input("\n¿Deseas enviar un SMS de prueba? (s/n): ")
    
    if respuesta.lower() != 's':
        print("Prueba de SMS cancelada")
        return False
    
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body="🚨 Prueba del sistema de monitoreo Costco MTY\n\nSi recibes este mensaje, tu configuración es correcta! ✓",
            from_=from_number,
            to=to_number
        )
        
        print(f"\n✓ SMS enviado correctamente!")
        print(f"✓ SID: {message.sid}")
        print(f"✓ Estado: {message.status}")
        print(f"\n📱 Revisa tu celular: {to_number}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error enviando SMS: {e}")
        print("\nPosibles causas:")
        print("1. El número de origen no es válido")
        print("2. El número de destino no está verificado (cuenta de prueba)")
        print("3. No tienes crédito suficiente")
        print("4. Las credenciales son incorrectas")
        return False


def main():
    """Función principal."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Prueba de Configuración de Twilio                              ║
║   Sistema de Monitoreo Costco MTY                                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Paso 1: Verificar credenciales
    if not test_twilio_credentials():
        print("\n❌ Configuración incompleta. Por favor configura las credenciales.")
        sys.exit(1)
    
    # Paso 2: Probar conexión
    if not test_twilio_connection():
        print("\n❌ No se pudo conectar con Twilio. Verifica tus credenciales.")
        sys.exit(1)
    
    # Paso 3: Enviar SMS de prueba
    test_send_sms()
    
    print("\n" + "="*70)
    print("PRUEBA COMPLETADA")
    print("="*70)
    print("\nSi todo funcionó correctamente, ya puedes ejecutar:")
    print("  python run_30min.py")
    print("\nPara recibir notificaciones cada 30 minutos.")


if __name__ == "__main__":
    main()

