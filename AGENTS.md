# AGENTS.md — BLANQUITA Vision

## 1. Propósito

Este archivo define las reglas obligatorias para cualquier agente de IA que analice, diseñe, documente, implemente, pruebe o modifique el proyecto **BLANQUITA Vision**.

Su objetivo es asegurar que todos los agentes trabajen de forma consistente, segura, trazable y alineada con la arquitectura y las SPECS aprobadas.

Este archivo NO reemplaza:

- `VISION_INTELIGENTE_BLQ.md`
- `ARQUITECTURA_CONEXION.md`
- `APP_MOVIL_BLANQ_V2.md`
- las SPECS ubicadas en `/specs`
- el código fuente
- los tests

Su función es definir **cómo debe trabajar un agente dentro del repositorio**.

---

## 2. Identidad del proyecto

**Nombre:** BLANQUITA Vision  
**Tipo:** Aplicación desktop de visión inteligente  
**Plataforma objetivo:** Windows 10 / Windows 11 de 64 bits  
**Lenguaje principal:** Python  
**Arquitectura:** Hexagonal / Ports & Adapters + Vision Pipeline

BLANQUITA Vision es el componente de percepción visual de un robot cartesiano.

Su responsabilidad principal es:

```text
capturar
↓
procesar
↓
detectar
↓
estimar posición
↓
validar
↓
generar VisionReport
↓
enviar al móvil
```

---

## 3. Principio arquitectónico fundamental

La separación de responsabilidades del sistema es:

```text
LAPTOP
BLANQUITA VISION
PERCEPCIÓN
      ↓
VisionReport
      ↓
MÓVIL
BLANQUITA MOBILE
DECISIÓN / SUPERVISIÓN
      ↓
MachineCommand
      ↓
ESP32
EJECUCIÓN / PROTECCIÓN
```

Principio rector:

> **La laptop percibe, el móvil decide y el ESP32 ejecuta y protege.**

BLANQUITA Vision:

```text
NO controla directamente al ESP32.
NO envía comandos de motores.
NO decide movimientos físicos.
NO se conecta al canal de control del ESP32.
NO sustituye validaciones de BLANQUITA Mobile.
```

Su salida principal es:

```text
VisionReport
```

---

## 4. Fuentes de verdad

Antes de realizar cualquier cambio, el agente debe leer las fuentes relevantes en este orden:

```text
1. AGENTS.md
2. VISION_INTELIGENTE_BLQ.md
3. ARQUITECTURA_CONEXION.md
4. APP_MOVIL_BLANQ_V2.md
5. SPEC correspondiente dentro de /specs
6. SPECS anteriores relevantes
7. Código existente
8. Tests existentes
```

La principal fuente técnica para BLANQUITA Vision es:

```text
VISION_INTELIGENTE_BLQ.md
```

`ARQUITECTURA_CONEXION.md` define las fronteras entre:

```text
Laptop
Móvil
ESP32
```

`APP_MOVIL_BLANQ_V2.md` debe utilizarse únicamente para comprender el contrato con la aplicación móvil.

---

## 5. Jerarquía documental

La jerarquía conceptual es:

```text
AGENTS.md
   ↓
Reglas para agentes

VISION_INTELIGENTE_BLQ.md
   ↓
Arquitectura global y baseline técnico

/specs
   ↓
Comportamiento detallado

/src
   ↓
Implementación

/tests
   ↓
Validación
```

La implementación debe seguir:

```text
Arquitectura aprobada
      ↓
SPEC aprobada
      ↓
Código
      ↓
Tests
```

Nunca asumir:

```text
"El código existente es correcto porque ya existe"
```

Si una SPEC aprobada contradice el código, el agente debe reportar la contradicción antes de modificar comportamiento.

---

## 6. Política de SPECS

Toda funcionalidad significativa debe estar asociada a una SPEC.

Las SPECS viven únicamente en:

```text
<RAIZ_PROYECTO>/specs/
```

La carpeta `/specs` YA EXISTE.

El agente NO debe:

- crear otra carpeta `specs`;
- crear `docs/specs`;
- mover la carpeta existente;
- renombrarla;
- guardar SPECS fuera de esa carpeta.

Antes de implementar una funcionalidad:

```text
1. Localizar la SPEC.
2. Leerla completamente.
3. Revisar su estado.
4. Revisar requisitos RF.
5. Revisar requisitos RNF.
6. Revisar casos de uso.
7. Revisar tests definidos.
8. Revisar criterios de aceptación.
9. Revisar dependencias.
10. Revisar decisiones abiertas.
```

---

## 7. Estados de una SPEC

Los estados posibles son:

```text
DRAFT
REVIEW
APPROVED
IMPLEMENTED
VALIDATED
```

### DRAFT

Puede modificarse cuando la tarea esté explícitamente relacionada con esa SPEC.

### REVIEW

Puede modificarse solo si la tarea actual es revisar/corregir esa SPEC.

### APPROVED

NO puede modificarse directamente.

Si el agente detecta un problema:

```text
1. Identificar la inconsistencia.
2. Explicar el impacto.
3. Indicar archivos/SPECS afectados.
4. Solicitar autorización.
5. No modificar la SPEC sin permiso.
```

### IMPLEMENTED

NO puede modificarse directamente sin autorización.

### VALIDATED

NO puede modificarse directamente sin autorización.

---

## 8. Catálogo oficial de SPECS

El proyecto se divide en:

```text
SPEC-00 — Fundación, arquitectura, UI y captura
SPEC-01 — Pipeline de visión, calibración, detección y estimación de posición
SPEC-02 — Protocolo, WebSocket, persistencia, analítica, reportes y diagnósticos
SPEC-03 — IA/ONNX, testing, rendimiento, tolerancia a fallos y release Windows
```

No adelantar funcionalidades de SPECS futuras sin autorización explícita.

---

## 9. Política de cero supuestos

El agente NO debe cerrar decisiones importantes basándose en:

- suposiciones;
- preferencias personales;
- interpretaciones ambiguas;
- convenciones no aprobadas;
- valores arbitrarios;
- inferencias sobre hardware;
- inferencias sobre UX;
- inferencias sobre protocolo;
- inferencias sobre calibración;
- inferencias sobre seguridad;
- inferencias sobre datos;
- inferencias sobre rendimiento.

Si falta información relevante, debe preguntar.

Antes de tomar una decisión material, comprobar:

```text
¿Está definida?
¿Está aprobada?
¿Existe en documentación?
¿Existe en la SPEC?
¿Afecta arquitectura?
¿Afecta protocolo?
¿Afecta UX?
¿Afecta hardware?
¿Afecta seguridad?
¿Afecta persistencia?
¿Afecta rendimiento?
¿Afecta SPECS futuras?
```

Si existe incertidumbre material:

```text
DETENERSE
↓
PREGUNTAR
↓
ESPERAR RESPUESTA
↓
CONTINUAR
```

---

## 10. No repetir preguntas resueltas

Antes de preguntar, buscar primero en:

```text
AGENTS.md
VISION_INTELIGENTE_BLQ.md
ARQUITECTURA_CONEXION.md
APP_MOVIL_BLANQ_V2.md
/specs
código
tests
```

No volver a preguntar una decisión ya cerrada salvo que:

- aparezca una contradicción nueva;
- una prueba demuestre que la decisión no funciona;
- exista una incompatibilidad técnica real;
- una SPEC posterior requiera reabrirla.

En ese caso debe explicarse por qué se reabre.

---

## 11. Stack tecnológico bloqueado

Baseline oficial:

```text
Windows 10 / Windows 11 x64
Python 3.13.16
uv 0.12.22
PySide6 6.11.2
PyQtGraph 0.14.0
NumPy 2.5.3
opencv-contrib-python-headless 4.14.0.94
ONNX Runtime 1.30.0
Pydantic 2.13.5
JSON
websockets 17.1
SQLite / sqlite3
Polars 1.44.2
pytest 9.1.1
PyInstaller 6.22.3
```

No actualizar dependencias unilateralmente.

No cambiar versiones por "usar la última".

No introducir frameworks alternativos.

No instalar nuevas dependencias sin autorización.

No modificar `uv.lock` como consecuencia de cambios de dependencias no aprobados.

---

## 12. Política específica de OpenCV

La distribución oficial es:

```text
opencv-contrib-python-headless==4.14.0.94
```

No instalar simultáneamente:

```text
opencv-python
opencv-python-headless
opencv-contrib-python
opencv-contrib-python-headless
```

Solo debe existir una variante OpenCV en el entorno.

La interfaz gráfica se gestiona mediante:

```text
PySide6
+
PyQtGraph
```

No usar `cv2.imshow()` como arquitectura principal de visualización.

---

## 13. Política de dependencias

Si el agente considera necesaria una nueva librería:

NO debe instalarla.

Debe:

```text
1. Explicar la necesidad.
2. Explicar por qué el stack actual no es suficiente.
3. Indicar impacto.
4. Proponer alternativa sin nueva dependencia si existe.
5. Solicitar autorización.
```

Solo después de autorización podrá modificarse:

```text
pyproject.toml
uv.lock
```

---

## 14. Idioma y convenciones

### Documentación

Idioma:

```text
Español
```

Incluye:

- README;
- SPECS;
- comentarios explicativos extensos;
- documentación arquitectónica;
- decisiones técnicas.

### Código

Los identificadores deben escribirse en inglés:

```text
classes
functions
methods
variables
modules
Python filenames
interfaces
ports
adapters
models
```

Ejemplos:

```text
CameraPort
OpenCvCamera
VisionPipeline
PositionEstimate
VisionReport
CalibrationService
```

### UI

Los mensajes visibles al usuario deben estar en:

```text
Español
```

### Protocolo

El protocolo JSON Laptop ↔ Mobile debe utilizar:

```text
Inglés
```

Ejemplos:

```text
vision.report
vision.ready
camera.status
calibration.status
```

---

## 15. Arquitectura obligatoria

El proyecto utiliza:

```text
Arquitectura Hexagonal
+
Ports & Adapters
+
Vision Pipeline
```

Capas:

```text
Presentation
     ↓
Application
     ↓
Domain
     ↑
Ports
     ↑
Adapters
```

Pipeline:

```text
Camera
  ↓
Capture
  ↓
Preprocess
  ↓
Detection
  ↓
Tracking
  ↓
Position Estimation
  ↓
Validation
  ↓
VisionReport
```

---

## 16. Reglas del Domain

El dominio debe mantenerse desacoplado de implementaciones concretas.

Evitar importar directamente en `domain/`:

```text
PySide6
cv2
websockets
sqlite3
onnxruntime
```

cuando exista una abstracción válida mediante Ports.

El dominio contiene conceptos como:

```text
Detection
PositionEstimate
VisionReport
VisionStatus
Calibration
CameraInfo
Session
Capture
Metric
```

---

## 17. Ports

Los Ports definen contratos.

Ejemplos:

```text
CameraPort
DetectorPort
PositionEstimatorPort
CalibrationRepositoryPort
ReportPublisherPort
VisionRepositoryPort
```

Los Ports:

- no deben conocer detalles de UI;
- no deben depender de hardware concreto;
- no deben depender innecesariamente de frameworks.

---

## 18. Adapters

Los Adapters implementan Ports.

Ejemplos:

```text
OpenCvCamera
OpenCvHookDetector
OnnxHookDetector
WebSocketVisionServer
SQLiteVisionRepository
```

La UI no debe acceder directamente a hardware o almacenamiento saltándose Application/Ports cuando la arquitectura ya define una abstracción.

---

## 19. Estructura del repositorio

Estructura esperada:

```text
blanquita_vision/
│
├── AGENTS.md
├── README.md
├── VISION_INTELIGENTE_BLQ.md
├── ARQUITECTURA_CONEXION.md
├── APP_MOVIL_BLANQ_V2.md
├── .python-version
├── pyproject.toml
├── uv.lock
│
├── specs/
│
├── src/
│   └── blanquita_vision/
│       ├── domain/
│       ├── application/
│       ├── adapters/
│       ├── infrastructure/
│       └── presentation/
│
├── tests/
├── models/
├── calibration/
└── data/
```

No crear nuevas carpetas de primer nivel sin una necesidad clara.

---

## 20. Reglas de organización del código

No colocar toda la lógica en:

```text
main.py
```

No colocar lógica de dominio en:

```text
presentation/
```

No importar UI desde:

```text
domain/
```

No saltarse Ports si ya existe una abstracción.

No duplicar lógica entre:

```text
presentation
application
adapters
```

Evitar clases con múltiples responsabilidades.

---

## 21. Reglas específicas de visión

El objetivo inicial es detectar:

```text
GANCHO DEL ROBOT CARTESIANO
```

El modelo de posición contempla:

```text
X
Y
Z
confidence
timestamp
angle opcional
```

Una coordenada no estimable debe poder ser:

```text
null
```

Nunca fabricar valores físicos.

Especialmente:

```text
Y = null
```

es válido mientras no exista una metodología de profundidad validada.

---

## 22. Política de IA / ML

Primera estrategia:

```text
OpenCV clásico
```

ONNX Runtime pertenece a:

```text
SPEC-03
```

No introducir ML antes de que corresponda a esa SPEC salvo autorización explícita.

Arquitectura esperada:

```text
DetectorPort
    ├── OpenCvHookDetector
    └── OnnxHookDetector
```

El resto del pipeline no debe depender del detector concreto.

---

## 23. Política de cámara

La cámara principal inicial es una webcam USB fija frente al cartesiano.

La arquitectura debe permitir reemplazarla.

No acoplar lógica de dominio a:

```text
índice de cámara
marca
modelo físico
resolución concreta
backend concreto
```

sin necesidad.

La captura deberá abstraerse mediante:

```text
CameraPort
```

---

## 24. Política de red

BLANQUITA Vision es:

```text
Servidor WebSocket
```

BLANQUITA Mobile es:

```text
Cliente WebSocket
```

Endpoint inicial:

```text
ws://IP_LAPTOP:8765/vision
```

No implementar MQTT.

No crear comunicación directa Laptop → ESP32.

---

## 25. Política de protocolo

Los mensajes deben ser estructurados.

Ejemplos:

```text
vision.hello
vision.ready
vision.status
vision.report
vision.error
vision.heartbeat
camera.status
calibration.status
```

Mobile → Laptop:

```text
vision.start
vision.stop
vision.ping
```

El protocolo debe validarse con:

```text
Pydantic
```

cuando corresponda.

---

## 26. Política de persistencia

SQLite almacena:

```text
metadata
datos estructurados
sesiones
detecciones
errores
eventos
calibraciones
referencias a capturas
```

Filesystem almacena:

```text
imágenes/capturas
```

No almacenar imágenes grandes como BLOB salvo decisión futura aprobada.

---

## 27. Política de video

V1:

```text
VIDEO EN VIVO
+
CAPTURAS PUNTUALES
```

No implementar grabación continua salvo cambio explícito de requisitos.

---

## 28. Concurrencia

El hilo principal de Qt debe gestionar principalmente UI.

No ejecutar en el hilo de UI:

- captura continua;
- procesamiento OpenCV pesado;
- inferencia ONNX;
- almacenamiento bloqueante;
- bucles WebSocket bloqueantes;
- operaciones largas.

Arquitectura esperada:

```text
Main/UI Thread
Camera Worker
Vision Worker
Network Worker
Storage Worker
cuando corresponda
```

No introducir `multiprocessing` sin evidencia de que es necesario.

---

## 29. Manejo de errores

Los errores deben tratarse explícitamente.

Ejemplos:

```text
cámara desconectada
frame inválido
modelo no disponible
WebSocket perdido
BD bloqueada
configuración inválida
archivo no encontrado
timeout
```

Un error no debe:

- bloquear permanentemente la UI;
- producir coordenadas falsas;
- producir movimiento físico;
- ocultarse silenciosamente.

---

## 30. Observabilidad

Registrar cuando corresponda:

```text
INFO
WARNING
ERROR
```

y métricas como:

```text
FPS captura
FPS pipeline
latencia preprocess
latencia detection
latencia position estimator
latencia total
latencia WebSocket
confidence
```

No registrar datos inútiles de forma excesiva.

---

## 31. Testing

Framework oficial:

```text
pytest==9.1.1
```

Antes de considerar una funcionalidad terminada, evaluar:

```text
unit tests
integration tests
negative tests
edge cases
hardware tests cuando corresponda
performance tests cuando corresponda
```

Una funcionalidad nueva debe incluir tests cuando su comportamiento sea automatizable.

No afirmar:

```text
"validado con hardware"
```

si solo se utilizó:

```text
mock
fake
fixture
simulación
```

Distinguir siempre:

```text
VALIDADO EN SOFTWARE
VALIDADO EN HARDWARE
```

---

## 32. Fakes y testabilidad

La arquitectura debe permitir sustituciones como:

```text
FakeCamera
FakeDetector
FakeMobileClient
InMemoryRepository
```

Evitar diseñar componentes imposibles de probar sin hardware cuando pueda existir una abstracción.

---

## 33. Política de métricas

No inventar objetivos como:

```text
latencia < 20 ms
FPS > 30
precisión > 99 %
```

si todavía no existen pruebas.

Utilizar:

```text
TBD — definir mediante benchmark
```

y especificar cómo se medirá.

---

## 34. Git — prohibición total para agentes

Los agentes NO tienen autorización para realizar ninguna operación Git.

Esto incluye, entre otros:

```text
git status
git diff
git add
git commit
git push
git pull
git fetch
git merge
git rebase
git checkout
git switch
git branch
git reset
git revert
git stash
git tag
git log
git clean
```

El agente NO debe:

- crear ramas;
- cambiar ramas;
- hacer commits;
- hacer push;
- hacer pull;
- hacer merge;
- hacer rebase;
- inspeccionar el repositorio mediante comandos Git;
- modificar configuración Git;
- eliminar ramas;
- restaurar archivos mediante Git.

Si necesita conocer cambios o estado del proyecto, debe utilizar:

```text
filesystem
archivos
tests
herramientas disponibles fuera de Git
```

Git queda exclusivamente bajo control del usuario.

---

## 35. Refactors

No realizar refactors masivos no solicitados.

No cambiar:

- nombres públicos;
- contratos;
- estructuras;
- APIs;
- modelos;
- directorios;
- protocolos;

solo porque el agente considere que "quedaría mejor".

Si un refactor amplio parece necesario:

```text
1. Explicar el problema.
2. Explicar el alcance.
3. Indicar archivos afectados.
4. Indicar riesgos.
5. Solicitar autorización.
```

---

## 36. Eliminación de archivos y funcionalidades

No borrar:

- archivos;
- carpetas;
- funcionalidades;
- tests;
- documentación;
- modelos;
- configuraciones;

sin autorización explícita cuando la eliminación sea material.

Si parece existir código obsoleto:

```text
1. Verificar referencias.
2. Verificar SPECS.
3. Verificar tests.
4. Explicar por qué parece obsoleto.
5. Pedir autorización.
```

---

## 37. Cambios de APIs

No renombrar o romper APIs públicas sin autorización.

Incluye:

```text
classes
functions
methods
ports
message types
JSON fields
database fields
settings keys
file formats
```

---

## 38. Política de cambios

Toda modificación debe mantenerse dentro del alcance solicitado.

Evitar:

```text
"ya que estoy aquí también cambiaré..."
```

No realizar limpieza incidental extensa.

No modificar módulos ajenos salvo que sea necesario para completar el requerimiento actual.

---

## 39. Flujo obligatorio antes de modificar código

Seguir:

```text
1. Leer AGENTS.md.
2. Leer documentación relevante.
3. Identificar SPEC.
4. Leer SPEC completa.
5. Leer SPECS relacionadas.
6. Inspeccionar código relacionado.
7. Inspeccionar tests relacionados.
8. Identificar dependencias.
9. Detectar contradicciones.
10. Detectar decisiones no cerradas.
11. Si falta una decisión material:
       DETENERSE.
       PREGUNTAR.
12. Preparar un plan mínimo.
13. Implementar solo el alcance solicitado.
14. Añadir/actualizar tests.
15. Ejecutar tests relevantes.
16. Revisar errores.
17. Actualizar documentación si corresponde.
18. Informar lo realizado.
```

---

## 40. Flujo para creación de SPECS

Cuando el usuario solicite:

```text
GENERAR SPEC-XX
```

seguir:

```text
1. Leer documentación base.
2. Leer SPECS anteriores relevantes.
3. Analizar dependencias.
4. Detectar ambigüedades.
5. Detectar decisiones no cerradas.
6. Detectar contradicciones.
7. Si existe una pregunta material:
      DETENERSE.
      PREGUNTAR.
      NO GENERAR TODAVÍA LA SPEC.
8. Incorporar respuestas.
9. Generar únicamente la SPEC solicitada.
10. Definir tests.
11. Crear trazabilidad.
12. Revisar completitud.
13. Guardar en:
    <RAIZ_PROYECTO>/specs/<NOMBRE_SPEC>.md
14. Verificar el archivo.
15. No avanzar automáticamente a la siguiente SPEC.
```

---

## 41. Protección de SPECS existentes

Antes de escribir una SPEC:

```text
comprobar si ya existe
```

Si NO existe:

```text
crear
```

Si existe:

```text
NO sobrescribir silenciosamente
```

Debe:

```text
1. Leerla.
2. Comprobar estado.
3. Comparar con la solicitud.
4. Informar al usuario.
5. Pedir autorización para reemplazar/actualizar si corresponde.
```

---

## 42. Convenciones de archivos Python

Los nombres de archivos Python deben utilizar:

```text
snake_case.py
```

Ejemplos:

```text
vision_pipeline.py
opencv_camera.py
position_estimate.py
websocket_vision_server.py
```

Clases:

```text
PascalCase
```

Ejemplos:

```text
VisionPipeline
OpenCvCamera
PositionEstimate
```

Funciones y variables:

```text
snake_case
```

---

## 43. Tipado

Utilizar type hints en código nuevo cuando mejoren claridad y mantenibilidad.

No introducir:

```text
mypy
pyright
ruff
```

ni otras herramientas de lint/type-checking no aprobadas.

No agregar herramientas nuevas de calidad sin autorización.

---

## 44. Formato

No se ha aprobado Ruff ni otro formatter externo.

El agente debe mantener:

- formato consistente;
- PEP 8 razonable;
- imports claros;
- funciones pequeñas cuando corresponda;
- nombres descriptivos.

No añadir una dependencia de formatter/linter.

---

## 45. Seguridad

BLANQUITA Vision es una fuente de percepción.

Nunca debe asumir:

```text
VisionReport
=
movimiento autorizado
```

Solo:

```text
VisionReport
=
observación
```

La decisión pertenece a BLANQUITA Mobile.

Datos recibidos por red deben validarse.

JSON malformado no debe provocar:

- crash;
- movimientos;
- corrupción de datos.

---

## 46. Tolerancia a fallos

La aplicación debe degradarse de forma segura.

### Sin móvil

```text
La visión local puede continuar.
No existe acción física.
```

### Cámara desconectada

```text
Estado de error.
Sin PositionEstimate válido.
```

### Detector falla

```text
No generar coordenadas falsas.
```

### GPU no disponible

```text
Fallback a CPU cuando esté soportado.
```

### WebSocket cae

```text
Visión local continúa.
Automatización móvil queda sin visión.
```

---

## 47. No acceso directo al ESP32

Está prohibido crear desde BLANQUITA Vision:

```text
WebSocket al ESP32
HTTP al ESP32
TCP directo al ESP32
MQTT directo al ESP32
serial de control al ESP32
```

salvo cambio de arquitectura aprobado explícitamente.

---

## 48. No sobreingeniería

Aplicar:

```text
SOLID
separation of concerns
dependency inversion
ports and adapters
single responsibility
testability
explicit state
fail safe
graceful degradation
```

Pero evitar:

- abstracciones innecesarias;
- patrones sin necesidad;
- microservicios;
- frameworks adicionales;
- capas artificiales;
- generalización prematura.

---

## 49. Definition of Done global

Una tarea se considera terminada cuando corresponda y se cumpla:

```text
✓ respeta AGENTS.md
✓ respeta VISION_INTELIGENTE_BLQ.md
✓ respeta la SPEC
✓ respeta arquitectura
✓ no introduce dependencias no aprobadas
✓ implementación completa
✓ tests relevantes creados/actualizados
✓ tests relevantes ejecutados
✓ criterios de aceptación cumplidos
✓ errores tratados
✓ documentación actualizada
✓ sin supuestos materiales ocultos
✓ sin responsabilidades del móvil trasladadas a la laptop
✓ sin acciones Git
```

Cuando aplique:

```text
✓ VALIDADO EN SOFTWARE
```

y si realmente se probó físicamente:

```text
✓ VALIDADO EN HARDWARE
```

---

## 50. Respuesta final del agente después de una tarea

Al terminar, informar de forma clara:

```text
Qué se hizo
Qué archivos se modificaron
Qué tests se ejecutaron
Resultado de los tests
Qué no pudo validarse
Decisiones abiertas
Riesgos detectados
Siguiente paso lógico
```

No afirmar éxito completo si existen pruebas pendientes.

---

## 51. Regla final

Ante cualquier duda material:

```text
NO asumir
↓
NO improvisar
↓
PREGUNTAR
```

Ante cualquier contradicción:

```text
NO sobrescribir
↓
REPORTAR
↓
PEDIR AUTORIZACIÓN
```

Ante cualquier cambio fuera del alcance:

```text
NO REALIZARLO
```

Ante cualquier operación Git:

```text
NO EJECUTARLA
```

Principio final:

> **BLANQUITA Vision debe evolucionar mediante SPECS, arquitectura explícita, pruebas verificables y decisiones aprobadas, sin supuestos silenciosos ni cambios autónomos fuera del alcance.**
