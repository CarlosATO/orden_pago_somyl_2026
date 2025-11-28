# Instrucciones para agregar el Logo de SOMYL

## Pasos para completar:

1. **Descarga el logo de SOMYL** desde esta URL:
   ```
   https://static.wixstatic.com/media/72c25d_3d90d3831e3e4165a106e50b39521e9a~mv2.png/v1/crop/x_144,y_282,w_1691,h_548/fill/w_636,h_206,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/72c25d_3d90d3831e3e4165a106e50b39521e9a~mv2.png
   ```
   
   O simplemente:
   - Abre https://www.somyl.com/ en tu navegador
   - Haz click derecho en el logo SOMYL (arriba a la izquierda)
   - Selecciona "Guardar imagen como..."

2. **Guarda el archivo** con el nombre `logo-somyl.png` en esta misma carpeta:
   ```
   /Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto/frontend/public/
   ```

3. **El index.html ya está configurado** para usar este logo como favicon.

4. **Reinicia el servidor frontend** (si está corriendo):
   ```bash
   # Detener: Ctrl+C
   # Iniciar: npm run dev
   ```

5. **Refresca el navegador** y verás el nuevo logo en la pestaña.

## Alternativa rápida (usando terminal):

Puedes descargar el logo directamente con este comando:

```bash
cd /Users/carlosalegria/Desktop/Migracion_OP/nuevo_proyecto/frontend/public
curl -o logo-somyl.png "https://static.wixstatic.com/media/72c25d_3d90d3831e3e4165a106e50b39521e9a~mv2.png/v1/crop/x_144,y_282,w_1691,h_548/fill/w_636,h_206,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/72c25d_3d90d3831e3e4165a106e50b39521e9a~mv2.png"
```

---

Una vez descargado el logo, ¡el favicon estará listo! 🎉
