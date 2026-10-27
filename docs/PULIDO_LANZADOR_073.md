# Panel Windows 0.7.3

La entrada principal es **Abrir SFA Aire**. Inicia o reutiliza el servidor de esta
carpeta y abre el portal. **Conectar Arduino** abre una sección del mismo sistema;
no crea otro modo ni elimina la autenticación o autorización del aula.

- Ícono oficial en ambos ejecutables, ventana y diálogos. ICO con siete tamaños.
- Jerarquía principal, controles de monitoreo y herramientas secundarias.
- Tipografía Segoe UI, estados de interacción y ventana compacta revisada en Windows.
- Estado diferenciado de servidor y demostración; actualización manual.
- Salida con tres alternativas: detener monitoreo y salir, mantenerlo y cerrar
  sólo el panel, o volver. Las acciones en curso impiden una salida ambigua.
- La detención verifica la identidad de esta instalación, conserva datos y no
  detiene servicios de otras carpetas. Las descargas Wi-Fi iniciadas por este
  panel se cierran con su árbol de procesos. Una descarga reutilizada de otro
  panel conserva su vencimiento temporal original.
- La guía HTML explica los controles vigentes. Windows 0.7.3 incluye APK 0.7.2.

Verificación: suite Python de 103 pruebas, build web, recursos ICO de los dos
ejecutables y revisión visual del panel y salida. El ZIP final se verifica con
`herramientas/verificar_portable.py`: arranque autónomo, simulación, puertos,
detención, demo aislada, descarga Wi-Fi e integridad. El informe del release
identifica el hash del ZIP comprobado.

Continúan pendientes el ensayo en otra PC física con Arduino, la primera
vinculación cloud de esa instalación y la ejecución de APK 0.7.2 en el Samsung.
Este ajuste no envía avisos reales ni cambia servicios cloud, cuotas o planes.
Los ejecutables mantienen su condición de piloto sin firma Authenticode.
