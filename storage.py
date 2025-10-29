"""
Módulo de almacenamiento para evitar duplicados.
"""

import os
from typing import Set


class NewsStorage:
    """Clase para gestionar el registro de noticias ya procesadas."""
    
    def __init__(self, storage_file: str):
        """
        Inicializa el almacenamiento.
        
        Args:
            storage_file: Ruta del archivo de almacenamiento
        """
        self.storage_file = storage_file
        self.processed_urls = self._load_processed()
    
    def _load_processed(self) -> Set[str]:
        """
        Carga las URLs de noticias ya procesadas.
        
        Returns:
            Conjunto de URLs procesadas
        """
        if not os.path.exists(self.storage_file):
            return set()
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"Error cargando noticias procesadas: {e}")
            return set()
    
    def is_processed(self, url: str) -> bool:
        """
        Verifica si una URL ya fue procesada.
        
        Args:
            url: URL de la noticia
        
        Returns:
            True si ya fue procesada, False en caso contrario
        """
        return url in self.processed_urls
    
    def mark_as_processed(self, url: str):
        """
        Marca una URL como procesada.
        
        Args:
            url: URL de la noticia
        """
        if url and url not in self.processed_urls:
            self.processed_urls.add(url)
            try:
                with open(self.storage_file, 'a', encoding='utf-8') as f:
                    f.write(f"{url}\n")
            except Exception as e:
                print(f"Error guardando URL procesada: {e}")
    
    def clear_old_entries(self, max_entries: int = 1000):
        """
        Limpia entradas antiguas si el archivo crece demasiado.
        
        Args:
            max_entries: Número máximo de entradas a mantener
        """
        if len(self.processed_urls) > max_entries:
            # Mantener solo las últimas max_entries
            recent_urls = list(self.processed_urls)[-max_entries:]
            self.processed_urls = set(recent_urls)
            
            try:
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    for url in recent_urls:
                        f.write(f"{url}\n")
            except Exception as e:
                print(f"Error limpiando archivo de almacenamiento: {e}")

