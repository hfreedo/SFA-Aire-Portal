# Evaluación de skills de diseño para SFA Aire

27/10/2026. Solicitud: evaluar si las herramientas enlazadas en el vídeo
https://youtu.be/mCWu9_Q2ltM pueden mejorar el criterio visual del proyecto.

Se obtuvieron los enlaces desde la descripción oficial de YouTube y se revisaron
los sitios y archivos de los autores. El endpoint público de subtítulos devolvió
vacío; no se presenta esta evaluación como una revisión de toda la narración.

## Recomendación

**Sí, integrar una selección por proyecto resulta recomendable.** Son guías de
trabajo y, según el paquete, scripts/herramientas de apoyo. No son una garantía
automática de calidad visual ni sustituyen revisar la APK ejecutada.

| Recurso | Encaje concreto | Recomendación |
| --- | --- | --- |
| [Impeccable](https://github.com/pbakaus/impeccable) | Guía específica para Android, incluidos Android Views; modos de producto, revisión visual, jerarquía, tipografía y adaptación nativa. | Primera opción para la app, con foco en su modo Operate y sus referencias Android. |
| [Wondel refactoring-ui](https://github.com/wondelai/skills/tree/main/refactoring-ui) | Jerarquía, escalas, espaciado, peso y estilos de acciones. Contiene ejemplos CSS que necesitan traducirse a dp/sp y componentes Android. | Complemento directo para la recomposición. |
| [Wondel ux-heuristics](https://github.com/wondelai/skills/tree/main/ux-heuristics) | Claridad de estados, consistencia, reconocimiento, navegación, errores y reducción de texto. | Complemento para conservar el recorrido sencillo de medir y notificar. |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill) | Dirección visual y referencias de pantallas de producto. Su flujo actual incluye scripts Node, inspección de navegador y recursos CSS. | Útil para el portal React; uso selectivo de sus principios en la APK, no traslado literal del flujo web. |

## Matices encontrados en las versiones actuales

- Impeccable 4.8.0 menciona explícitamente Android Views y Material 3. Sus
  detectores de markup/DOM no certifican una APK. La revisión nativa requiere
  capturas y comprobación del resultado real.
- Su instalación completa incluye un lanzador/motor y puede añadir hooks.
  Evaluar instrucciones no equivale a instalarlo ni autorizar esos hooks.
- Wondel ofrece muchas categorías ajenas al objetivo. Empezar con las dos guías
  anteriores, sin sumar marketing, captación o monetización a una herramienta escolar.
- Taste tiene instrucciones específicas para pantallas de aplicación, pero el
  material consultado está basado principalmente en pantallas web de escritorio.
  Su sitio y la estructura actual del repositorio no deben tratarse como versiones
  inmutables; revisar los archivos exactos antes de instalar.

## Cómo convertirlo en mejora comprobable

1. Mantener como contexto el objetivo escolar, el usuario docente y el uso en A02.
2. Fijar un sistema visual por funciones: tipografía, espaciado, superficies,
   acciones y estados; conservar marca y reglas del sistema.
3. Recomponer Mi aula, Avisos y Ajustes juntas, usando como línea de base la
   [auditoría visual de 0.7.4](AUDITORIA_VISUAL_ANDROID_074.md).
4. Ejecutar la APK, recorrer estados, mirar las tres pantallas y corregir el
   resultado. La interpolación y las pruebas funcionales no validan por sí solas
   composición, legibilidad ni acabado.
5. Registrar un antes/después a la misma densidad, tamaño de letra y datos antes
   de publicar. Mantener el ensayo físico como una verificación separada.

La integración de guías de desarrollo no exige cambiar Supabase Free/Firebase
Spark. Debe respetar el proyecto independiente, sus permisos, sus datos y la
prohibición de incorporar servicios pagos por una mejora visual.

## Procedencia revisada y estado

- Impeccable: `d34c87e1a00989ae8dbdd7f6b30b70f23319e860`.
- Wondel: `c172996495bed0fcd26896a9416b2093fd7073f0`.
- Taste Skill: `12af471f627f866411b4bd785b19646d3672784c`.
- Documentación oficial de skills: https://learn.chatgpt.com/docs/build-skills

Estado actualizado el 27/10/2026: **instaladas por proyecto y aplicadas a la
revisión**, sin hooks automáticos. Impeccable, refactoring-ui y ux-heuristics
están en `.agents/skills/`; se usaron los commits fijados arriba y el instalador
oficial de skills de Codex. Taste no se instaló.

Se ejecutó una vez el cargador `impeccable context`, cuyo lanzador verifica el
motor descargado contra su manifiesto de checksums. Las guías se leyeron en esta
sesión; su descubrimiento automático como skills ocurre en la siguiente sesión.
El inventario local reproducible está en `.agents/skills/sfa-design-lock.json`.

Resultado: [plan de mejora con evidencia](PLAN_MEJORA_UX_SKILLS.md) y
[criterios de diseño para implementar](CRITERIOS_DISENO_UI.md). Instalar las guías
no modifica por sí solo la aplicación ni certifica la estética de una release.
