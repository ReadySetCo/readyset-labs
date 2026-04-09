# Instrucciones para Exportar Cookies de Facebook

Para que el scraper pueda descargar videos de Meta Ad Library, necesitás exportar tus cookies de Facebook una sola vez.

## Pasos:

### 1. Instalar extensión Cookie Editor
- Chrome: [Cookie Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- Firefox: [Cookie Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
- Edge: Buscar "Cookie Editor" en extensions

### 2. Ir a Facebook y asegurarte de estar logueado
- Abrí https://www.facebook.com
- Asegurate de estar logueado con tu cuenta

### 3. Exportar las cookies
1. Hacé click en el ícono de Cookie Editor en la barra de extensiones
2. Hacé click en "Export" (ícono de descarga)
3. Seleccioná formato "Netscape" (importante!)
4. Copiá todo el texto

### 4. Guardar el archivo
1. Creá un archivo llamado `facebook_cookies.txt` en este directorio:
   `c:\Users\Lauta\Documents\SCRAPPER\backend\facebook_cookies.txt`
2. Pegá las cookies y guardá el archivo

### 5. Verificar
Corré este comando para verificar:
```
.\venv\Scripts\python.exe -c "from pathlib import Path; print('OK' if Path('facebook_cookies.txt').exists() else 'NOT FOUND')"
```

## Notas:
- Las cookies expiran después de un tiempo (semanas/meses)
- Si los videos dejan de descargarse, repetí el proceso
- El archivo NO se sube a git (está en .gitignore)
