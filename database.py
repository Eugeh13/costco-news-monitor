"""
Módulo de gestión de base de datos PostgreSQL para el sistema de monitoreo.
Maneja almacenamiento, detección de duplicados y tracking de noticias.
"""

import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Tuple

# Zona horaria Central
CENTRAL_TZ = pytz.timezone('America/Chicago')


class NewsDatabase:
    """Gestor de base de datos para noticias de alto impacto."""
    
    def __init__(self):
        """Inicializa la conexión a la base de datos."""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            print("⚠️  DATABASE_URL no configurada, modo sin base de datos")
            self.enabled = False
        else:
            self.enabled = True
            print("✓ Conexión a base de datos configurada")
    
    def get_connection(self):
        """
        Obtiene una conexión a la base de datos.
        
        Returns:
            psycopg2.connection: Conexión a PostgreSQL
        """
        if not self.enabled:
            return None
        
        try:
            conn = psycopg2.connect(self.db_url)
            return conn
        except Exception as e:
            print(f"⚠️  Error conectando a la base de datos: {e}")
            return None
    
    def initialize_schema(self):
        """Crea las tablas si no existen."""
        if not self.enabled:
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            with open('database_schema.sql', 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            cursor = conn.cursor()
            cursor.execute(schema_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✓ Esquema de base de datos inicializado")
            return True
        except Exception as e:
            print(f"⚠️  Error inicializando esquema: {e}")
            if conn:
                conn.close()
            return False
    
    @staticmethod
    def generate_hash(titulo: str) -> str:
        """
        Genera un hash único para una noticia basado en su título normalizado.
        
        Args:
            titulo: Título de la noticia
            
        Returns:
            str: Hash MD5 del título normalizado
        """
        # Normalizar: minúsculas, sin espacios extra, sin puntuación
        normalized = titulo.lower().strip()
        normalized = ' '.join(normalized.split())  # Espacios únicos
        
        # Generar hash MD5
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, titulo: str, url: str, fuente: str, max_hours: int = 24) -> bool:
        """
        Verifica si una noticia es duplicada.
        
        Args:
            titulo: Título de la noticia
            url: URL de la noticia
            fuente: Fuente de la noticia
            max_hours: Ventana de tiempo para considerar duplicados (horas)
            
        Returns:
            bool: True si es duplicada, False si es nueva
        """
        if not self.enabled:
            return False
        
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            noticia_hash = self.generate_hash(titulo)
            cutoff_time = datetime.now(CENTRAL_TZ) - timedelta(hours=max_hours)
            
            # Buscar por hash o por URL+fuente
            query = """
                SELECT id FROM noticias 
                WHERE (noticia_hash = %s OR (url = %s AND fuente = %s))
                  AND fecha_deteccion >= %s
                LIMIT 1
            """
            cursor.execute(query, (noticia_hash, url, fuente, cutoff_time))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result is not None
        except Exception as e:
            print(f"⚠️  Error verificando duplicado: {e}")
            if conn:
                conn.close()
            return False
    
    def save_noticia(self, noticia_data: Dict) -> Optional[int]:
        """
        Guarda una noticia en la base de datos.
        
        Args:
            noticia_data: Diccionario con los datos de la noticia
            
        Returns:
            int: ID de la noticia guardada, o None si hubo error
        """
        if not self.enabled:
            return None
        
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Generar hash
            noticia_hash = self.generate_hash(noticia_data['titulo'])
            
            # Preparar datos
            query = """
                INSERT INTO noticias (
                    noticia_hash, titulo, descripcion, url, fuente,
                    categoria, severidad,
                    ubicacion_texto, latitud, longitud,
                    costco_nombre, costco_distancia_km,
                    victimas, heridos, impacto_trafico, servicios_emergencia,
                    fecha_evento, fecha_publicacion,
                    alerta_enviada
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s
                )
                RETURNING id
            """
            
            values = (
                noticia_hash,
                noticia_data.get('titulo'),
                noticia_data.get('descripcion'),
                noticia_data.get('url'),
                noticia_data.get('fuente'),
                noticia_data.get('categoria'),
                noticia_data.get('severidad'),
                noticia_data.get('ubicacion_texto'),
                noticia_data.get('latitud'),
                noticia_data.get('longitud'),
                noticia_data.get('costco_nombre'),
                noticia_data.get('costco_distancia_km'),
                noticia_data.get('victimas', 0),
                noticia_data.get('heridos', 0),
                noticia_data.get('impacto_trafico'),
                noticia_data.get('servicios_emergencia', False),
                noticia_data.get('fecha_evento'),
                noticia_data.get('fecha_publicacion'),
                noticia_data.get('alerta_enviada', False)
            )
            
            cursor.execute(query, values)
            noticia_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✓ Noticia guardada en DB (ID: {noticia_id})")
            return noticia_id
        except Exception as e:
            print(f"⚠️  Error guardando noticia: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return None
    
    def mark_alert_sent(self, noticia_id: int):
        """
        Marca una noticia como que ya se envió alerta.
        
        Args:
            noticia_id: ID de la noticia
        """
        if not self.enabled:
            return
        
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query = """
                UPDATE noticias 
                SET alerta_enviada = TRUE, fecha_alerta = NOW()
                WHERE id = %s
            """
            cursor.execute(query, (noticia_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️  Error marcando alerta: {e}")
            if conn:
                conn.close()
    
    def start_execution(self) -> Optional[int]:
        """
        Registra el inicio de una ejecución de monitoreo.
        
        Returns:
            int: ID de la ejecución, o None si hubo error
        """
        if not self.enabled:
            return None
        
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO ejecuciones_monitoreo (estado)
                VALUES ('en_proceso')
                RETURNING id
            """
            cursor.execute(query)
            execution_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return execution_id
        except Exception as e:
            print(f"⚠️  Error registrando ejecución: {e}")
            if conn:
                conn.close()
            return None
    
    def end_execution(self, execution_id: int, stats: Dict):
        """
        Registra el fin de una ejecución de monitoreo.
        
        Args:
            execution_id: ID de la ejecución
            stats: Estadísticas de la ejecución
        """
        if not self.enabled or not execution_id:
            return
        
        conn = self.get_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            query = """
                UPDATE ejecuciones_monitoreo 
                SET fecha_fin = NOW(),
                    noticias_analizadas = %s,
                    noticias_nuevas = %s,
                    noticias_duplicadas = %s,
                    alertas_enviadas = %s,
                    estado = %s,
                    mensaje_error = %s
                WHERE id = %s
            """
            values = (
                stats.get('noticias_analizadas', 0),
                stats.get('noticias_nuevas', 0),
                stats.get('noticias_duplicadas', 0),
                stats.get('alertas_enviadas', 0),
                stats.get('estado', 'completado'),
                stats.get('mensaje_error'),
                execution_id
            )
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️  Error finalizando ejecución: {e}")
            if conn:
                conn.close()
    
    def get_recent_news(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        Obtiene las noticias recientes.
        
        Args:
            hours: Ventana de tiempo en horas
            limit: Número máximo de noticias
            
        Returns:
            List[Dict]: Lista de noticias
        """
        if not self.enabled:
            return []
        
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cutoff_time = datetime.now(CENTRAL_TZ) - timedelta(hours=hours)
            
            query = """
                SELECT * FROM noticias
                WHERE fecha_evento >= %s
                ORDER BY fecha_evento DESC
                LIMIT %s
            """
            cursor.execute(query, (cutoff_time, limit))
            noticias = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(n) for n in noticias]
        except Exception as e:
            print(f"⚠️  Error obteniendo noticias recientes: {e}")
            if conn:
                conn.close()
            return []
