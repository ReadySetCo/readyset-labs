# Cómo configurar Facebook Cookies para descarga de videos

El sistema necesita cookies de Facebook para descargar videos del Ad Library cuando no puede usar Apify.

## Método 1: Usar extensión del navegador (Recomendado)

1. Instala la extensión "Get cookies.txt LOCALLY" en Chrome/Firefox
2. Inicia sesión en Facebook.com
3. Ve a cualquier página de Facebook
4. Haz clic en la extensión y exporta las cookies
5. Guarda el archivo como `facebook_cookies.txt` en la carpeta `backend/`

## Método 2: Exportar manualmente

1. Abre Chrome DevTools (F12) en Facebook
2. Ve a Application → Cookies → facebook.com
3. Exporta en formato Netscape

## Formato del archivo

El archivo debe verse así:
```
# Netscape HTTP Cookie File
.facebook.com	TRUE	/	TRUE	1735689600	c_user	YOUR_USER_ID
.facebook.com	TRUE	/	TRUE	1735689600	xs	YOUR_SESSION
.facebook.com	TRUE	/	TRUE	1735689600	datr	YOUR_DATR
```

## Importante

- Las cookies expiran, renovarlas cada 1-2 semanas
- Nunca compartas este archivo (contiene tu sesión)


