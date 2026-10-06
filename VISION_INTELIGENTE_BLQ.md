# VISION_INTELIGENTE_BLQ

## 1. Identificación del componente

**Nombre:** BLANQUITA Vision  
**Tipo:** Aplicación desktop de visión inteligente  
**Plataforma objetivo:** Windows 10 / Windows 11 de 64 bits  
**Lenguaje principal:** Python  
**Versión inicial del documento:** V1  
**Fecha de baseline técnico:** 6 de octubre de 2026

BLANQUITA Vision será el programa de escritorio encargado de la **percepción visual** del proyecto BLANQUITA.

Su responsabilidad será capturar video desde una cámara USB, procesar las imágenes, localizar inicialmente la posición del gancho del robot cartesiano, calcular estimaciones espaciales, generar reportes estructurados y enviarlos a la aplicación móvil mediante WebSocket.

BLANQUITA Vision **no controlará directamente al ESP32**.

La arquitectura general del sistema se mantiene:

```text
LAPTOP
BLANQUITA VISION
PERCEPCIÓN
      │
      │ VisionReport
      ▼
MÓVIL
BLANQUITA MOBILE
DECISIÓN + SUPERVISIÓN
      │
      │ MachineCommand
      ▼
ESP32
EJECUCIÓN + PROTECCIÓN
```

Principio rector:

> **La laptop percibe, el móvil decide y el ESP32 ejecuta y protege.**

---

# 2. Hardware objetivo

El entorno principal de desarrollo y ejecución será una laptop con características aproximadas:

```text
Sistema operativo:
Windows 10 / Windows 11 64 bits

CPU:
AMD Ryzen 5 8645HS

GPU integrada:
AMD Radeon 760M Graphics

GPU dedicada:
NVIDIA GeForce RTX 4050 Laptop GPU
6 GB VRAM

RAM:
16 GB DDR5

Almacenamiento disponible:
Más de 100 GB libres
```

Este hardware es suficiente para:

- Captura de video en tiempo real.
- Procesamiento OpenCV.
- Visualización gráfica.
- Calibración.
- Inferencia ONNX en CPU.
- Inferencia ONNX acelerada por GPU en una etapa posterior.
- Analítica local.
- Persistencia SQLite.
- Ejecución simultánea de la interfaz, pipeline de visión y servidor WebSocket.

---

# 3. Cámara

La cámara principal inicial será la webcam USB definida para el proyecto BLANQUITA.

La cámara estará:

- Conectada directamente a la laptop.
- Instalada en una posición fija.
- Frente al robot cartesiano.
- A una altura ligeramente superior al área de trabajo.
- Orientada hacia la zona donde se encuentra el gancho y el espacio de operación.

La arquitectura **no debe acoplarse a un modelo físico específico de cámara**.

Debe ser posible reemplazar la cámara en el futuro por:

- Una webcam de mayor resolución.
- Una cámara con mejor óptica.
- Una cámara industrial.
- Otro dispositivo compatible con Windows/OpenCV.

Por ese motivo la captura se abstraerá mediante un puerto/interfaz de cámara.

---

# 4. Objetivo inicial de visión

La primera tarea principal del visor será:

> **Detectar y estimar la posición del gancho del robot cartesiano.**

El sistema deberá identificar el gancho dentro de la escena y producir una estimación estructurada.

Modelo objetivo:

```text
PositionEstimate

X
Y
Z
confidence
timestamp
angle (opcional)
```

Donde:

```text
X
= posición horizontal

Y
= profundidad / componente espacial adicional

Z
= altura

confidence
= nivel de confianza de la estimación

timestamp
= instante al que corresponde la medición

angle
= orientación del gancho, opcional
```

## Nota importante sobre X/Y/Z

El modelo de dominio estará preparado desde V1 para manejar:

```text
X
Y
Z
```

Sin embargo, una cámara monocular fija no garantiza por sí sola una medición métrica tridimensional precisa de los tres ejes.

Por lo tanto:

- El contrato soportará X/Y/Z.
- X y Z podrán ser los primeros ejes validados si el movimiento ocurre sobre un plano calibrado.
- Y solo se considerará una coordenada físicamente válida cuando exista una metodología de calibración/estimación que la respalde.
- No se inventarán valores de profundidad.
- Si un eje todavía no puede estimarse de manera fiable, se representará como no disponible.

La precisión real deberá validarse experimentalmente.

---

# 5. Enfoque de visión

Se utilizará un enfoque **híbrido**.

El proyecto no dependerá obligatoriamente de inteligencia artificial desde el primer prototipo.

Orden recomendado:

```text
1. Calibración

2. Visión clásica OpenCV

3. Geometría / contornos / marcadores / homografía

4. Evaluación de precisión

5. Machine Learning cuando aporte una mejora real
```

La IA se incorporará solamente cuando:

- la visión clásica no sea suficientemente robusta;
- existan variaciones complejas de iluminación;
- la forma del gancho sea difícil de segmentar;
- existan oclusiones;
- sea necesario generalizar a distintos objetos;
- el rendimiento de un detector ML sea claramente superior.

---

# 6. Stack tecnológico oficial

La siguiente matriz constituye el **baseline técnico inicial** de BLANQUITA Vision.

Las versiones se fijarán exactamente en el proyecto y en el lockfile.

| Área | Tecnología | Versión baseline | Uso |
|---|---|---:|---|
| Lenguaje | Python | 3.13.16 | Lenguaje principal |
| Gestión de entorno | uv | 0.12.22 | Python, `.venv`, dependencias y lock |
| UI | PySide6 | 6.11.2 | Aplicación desktop Qt |
| Visualización | PyQtGraph | 0.14.0 | Video, gráficos y métricas en tiempo real |
| Cálculo | NumPy | 2.5.3 | Arrays y procesamiento numérico |
| Visión | opencv-contrib-python-headless | 4.14.0.94 | OpenCV + módulos contrib |
| Inferencia inicial | ONNX Runtime | 1.30.0 | Inferencia ML en CPU |
| Inferencia GPU futura | onnxruntime-gpu | 1.30.0 | Inferencia con RTX 4050 |
| Modelos de datos | Pydantic | 2.13.5 | Validación y serialización |
| Protocolo | JSON | Estándar | Intercambio Laptop ↔ Mobile |
| Red | websockets | 17.1 | Servidor WebSocket |
| Persistencia | sqlite3 / SQLite | incluido con Python | Base de datos local |
| Analítica | Polars | 1.44.2 | Análisis tabular opcional |
| Testing | pytest | 9.1.1 | Pruebas unitarias/integración |
| Empaquetado Windows | PyInstaller | 6.22.3 | Generar aplicación `.exe` |

---

# 7. Decisiones sobre versiones

## 7.1. Python 3.13.16

Se fija:

```text
Python 3.13.16
```

como baseline del proyecto.

El entorno se construirá específicamente sobre esta versión.

Se utilizará:

```text
.python-version
```

para documentar la versión del intérprete.

---

## 7.2. PySide6 6.11.2

Será el framework principal de escritorio.

Responsabilidades:

- Ventana principal.
- Navegación.
- Paneles.
- Controles.
- Diálogos.
- Tablas.
- Configuración.
- Eventos.
- Señales/slots.
- Gestión del hilo principal de UI.

Se utilizará principalmente:

```text
Qt Widgets
```

No se utilizará QML inicialmente.

---

## 7.3. PyQtGraph 0.14.0

Complementará PySide6.

Responsabilidades:

- Mostrar frames.
- Gráficas FPS.
- Latencia.
- Tiempo de inferencia.
- Confidence.
- Posición X/Y/Z.
- Evolución temporal.
- Métricas de sesión.

El programa tendrá un enfoque de **consola técnica de visión**, no únicamente un reproductor de cámara.

---

# 8. OpenCV

Se fija:

```text
opencv-contrib-python-headless==4.14.0.94
```

y NO:

```text
opencv-python
```

ni:

```text
opencv-contrib-python
```

como paquete base.

Razón:

La interfaz gráfica será gestionada por:

```text
PySide6
+
PyQtGraph
```

Por tanto, no necesitamos las capacidades GUI propias de OpenCV como:

```text
cv2.imshow()
```

La variante headless reduce dependencias gráficas duplicadas y disminuye el riesgo de conflictos Qt.

Además se elige `contrib` porque permite disponer de módulos adicionales útiles para:

- ArUco.
- Calibración.
- Features.
- Tracking.
- Algoritmos adicionales de visión.

Importante:

> Solo debe existir **una distribución OpenCV** dentro del entorno.

No instalar simultáneamente:

```text
opencv-python
opencv-python-headless
opencv-contrib-python
opencv-contrib-python-headless
```

---

# 9. NumPy

Se fija:

```text
numpy==2.5.3
```

Uso:

- Frames representados como arrays.
- Transformaciones.
- Matrices.
- Vectores.
- Coordenadas.
- Cálculos de calibración.
- Datos de entrada/salida del detector.
- Integración con OpenCV y ONNX Runtime.

OpenCV 4.14.0.94 declara para Python moderno:

```text
numpy >= 2
```

por lo que el baseline utiliza NumPy 2.x.

---

# 10. ONNX Runtime

Baseline inicial:

```text
onnxruntime==1.30.0
```

Durante las primeras etapas se utilizará CPU.

Esto permite desarrollar primero:

```text
cámara
↓
OpenCV
↓
pipeline
↓
detección
↓
estimación
```

sin introducir dependencias CUDA prematuramente.

---

# 11. ONNX Runtime GPU

La laptop dispone de:

```text
RTX 4050 6 GB
```

por lo que la aplicación podrá evolucionar hacia:

```text
onnxruntime-gpu==1.30.0
```

No se instalarán simultáneamente las variantes CPU y GPU sin una razón concreta.

La activación de GPU se realizará como una etapa independiente.

Antes de habilitar GPU se verificará:

```text
driver NVIDIA
CUDA compatible
cuDNN
ExecutionProvider disponible
modelo ONNX
VRAM
latencia
```

La aplicación deberá soportar fallback:

```text
CUDAExecutionProvider
        ↓ si no disponible
CPUExecutionProvider
```

---

# 12. Pydantic

Se fija:

```text
pydantic==2.13.5
```

Responsabilidades:

- Modelos tipados.
- Validación de mensajes.
- Parseo JSON.
- Validación de configuración.
- Contrato Laptop ↔ Mobile.
- Prevención de datos incompletos o inválidos.

Ejemplos de modelos:

```text
VisionReport

PositionEstimate

VisionStatus

CameraStatus

CalibrationStatus

VisionError
```

---

# 13. WebSockets

Se fija:

```text
websockets==17.1
```

BLANQUITA Vision funcionará como:

```text
SERVIDOR WEBSOCKET
```

Endpoint inicial:

```text
ws://IP_LAPTOP:8765/vision
```

La aplicación móvil será:

```text
CLIENTE WEBSOCKET
```

El canal transportará únicamente información y comandos relacionados con visión.

---

# 14. SQLite

Se utilizará:

```text
sqlite3
```

incluido en la librería estándar de Python.

La base de datos será local.

Se utilizará para:

- Configuración.
- Calibraciones.
- Sesiones.
- Detecciones.
- Reportes.
- Eventos.
- Errores.
- Métricas.
- Referencias a capturas.

---

# 15. Capturas de imágenes

Las imágenes NO se almacenarán como blobs grandes dentro de SQLite.

Arquitectura:

```text
captura física
   ↓
archivo .jpg/.png
   ↓
data/captures/
   ↓
SQLite guarda:
ruta
fecha
evento
detección
metadata
```

---

# 16. Video

V1 tendrá:

```text
VIDEO EN VIVO
```

y:

```text
CAPTURAS PUNTUALES
```

No se implementará inicialmente:

```text
grabación continua de sesiones completas
```

---

# 17. Polars

Se fija como componente opcional:

```text
polars==1.44.2
```

Se utilizará cuando el módulo Analítica necesite trabajar con volúmenes mayores de:

```text
detecciones
sesiones
FPS
latencias
confidence
errores
coordenadas
```

No participa en el pipeline crítico de video.

---

# 18. Pytest

Se fija:

```text
pytest==9.1.1
```

Se utilizará para:

- Domain tests.
- Pipeline tests.
- Model validation.
- Camera mocks.
- Detector mocks.
- WebSocket tests.
- Database tests.
- Integration tests.

---

# 19. PyInstaller

Se fija:

```text
pyinstaller==6.22.3
```

El desarrollo normal utilizará:

```text
Python
+
.venv
+
uv
```

pero la distribución final deberá permitir generar:

```text
BLANQUITA_VISION.exe
```

para Windows.

---

# 20. Gestión de entorno

Se utilizará:

```text
uv
```

Versión baseline:

```text
uv==0.12.22
```

El proyecto tendrá:

```text
.python-version
pyproject.toml
uv.lock
.venv/
```

El `.venv` será local y NO se versionará.

Sí se versionarán:

```text
.python-version
pyproject.toml
uv.lock
```

---

# 21. Política de dependencias

Las dependencias se fijarán mediante versiones exactas.

Ejemplo:

```toml
dependencies = [
    "PySide6==6.11.2",
    "pyqtgraph==0.14.0",
    "numpy==2.5.3",
    "opencv-contrib-python-headless==4.14.0.94",
    "pydantic==2.13.5",
    "websockets==17.1",
]
```

Desarrollo:

```text
pytest==9.1.1
pyinstaller==6.22.3
```

Fase ML:

```text
onnxruntime==1.30.0
```

Analítica:

```text
polars==1.44.2
```

---

# 22. Política de actualización

No se actualizará automáticamente una dependencia solo porque exista una versión más nueva.

Flujo:

```text
nueva versión
      ↓
rama de actualización
      ↓
uv lock
      ↓
tests
      ↓
smoke test
      ↓
cámara
      ↓
pipeline
      ↓
WebSocket
      ↓
calibración
      ↓
rendimiento
      ↓
merge
```

---

# 23. Idea general del programa

BLANQUITA Vision será una aplicación desktop que permite:

```text
Conectar cámara
      ↓
Mostrar video en vivo
      ↓
Calibrar sistema
      ↓
Detectar gancho
      ↓
Estimar posición
      ↓
Validar resultado
      ↓
Mostrar información
      ↓
Registrar reporte
      ↓
Enviar VisionReport al móvil
```

El sistema debe continuar ejecutándose aunque el móvil esté temporalmente desconectado.

---

# 24. Módulos funcionales V1

Todas las siguientes secciones forman parte de V1:

```text
LIVE

CALIBRACIÓN

DETECCIÓN

ANALÍTICA

REPORTES

DIAGNÓSTICOS

AJUSTES
```

---

# 25. LIVE

Debe mostrar:

```text
Video en vivo
Bounding boxes / overlays
Punto detectado
X / Y / Z
Confidence
Ángulo si existe
FPS
Tiempo procesamiento
Estado cámara
Estado detector
Estado móvil
Estado calibración
```

---

# 26. CALIBRACIÓN

Responsabilidades:

- Seleccionar método de calibración.
- Detectar patrón.
- Calcular parámetros.
- Ver error.
- Guardar calibración.
- Recuperar calibración.
- Invalidar calibración cuando cambie la cámara/posición.

Puede utilizar:

```text
Chessboard
ArUco
Homografía
Puntos de referencia
```

---

# 27. DETECCIÓN

Permitirá:

- Encender/apagar detector.
- Ver parámetros.
- Ver confidence.
- Ver posición.
- Ver overlays.
- Seleccionar detector.
- Comparar resultados.

La implementación debe desacoplar:

```text
OpenCvDetector
```

de:

```text
OnnxDetector
```

---

# 28. ANALÍTICA

Debe mostrar métricas como:

```text
FPS
latencia pipeline
tiempo preprocess
tiempo detección
tiempo postprocess
confidence
posición X
posición Y
posición Z
detecciones por minuto
errores
```

PyQtGraph será la herramienta principal para gráficos en tiempo real.

Polars será opcional para análisis históricos.

---

# 29. REPORTES

Permitirá consultar:

```text
sesiones
detecciones
capturas
errores
calibraciones
eventos
```

Funciones:

- Buscar.
- Filtrar.
- Abrir captura.
- Exportar JSON.
- Exportar CSV.

---

# 30. DIAGNÓSTICOS

Mostrará información técnica sobre:

```text
CAMERA
VISION
MODEL
NETWORK
DATABASE
SYSTEM
```

Incluyendo:

```text
dispositivo
backend
resolución
FPS
pipeline FPS
tiempos
provider ONNX
modelo
WebSocket
latencia
estado BD
CPU
RAM
GPU
```

---

# 31. AJUSTES

Configuraciones previstas:

```text
Cámara
Resolución
FPS
Backend captura
Detector
Modelo ONNX
Confidence mínima
Calibración
Ruta datos
WebSocket
Puerto
Capturas
Analítica
Logs
```

---

# 32. Patrón arquitectónico

BLANQUITA Vision utilizará:

> **Arquitectura Hexagonal / Ports & Adapters combinada con un Pipeline de Visión.**

Representación:

```text
                    PRESENTATION
                     PySide6/UI
                         │
                         ▼
                    APPLICATION
                Casos de uso/servicios
                         │
                         ▼
                      DOMAIN
         Detection / Position / VisionReport
                         ▲
                         │
                       PORTS
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
 CameraPort         DetectorPort       ReportPort
       ▲                 ▲                 ▲
       │                 │                 │
    ADAPTERS          ADAPTERS          ADAPTERS
       │                 │                 │
    OpenCV         OpenCV / ONNX       WebSocket
```

---

# 33. Domain

Modelos principales:

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

# 34. Ports

Interfaces previstas:

```text
CameraPort
DetectorPort
PositionEstimatorPort
CalibrationRepositoryPort
ReportPublisherPort
VisionRepositoryPort
```

---

# 35. Adapters

Implementaciones concretas:

```text
OpenCvCamera
OpenCvHookDetector
OnnxHookDetector
WebSocketVisionServer
SQLiteVisionRepository
```

---

# 36. Pipeline de visión

Pipeline principal:

```text
CAMERA
   │
   ▼
CAPTURE
   │
   ▼
PREPROCESS
   │
   ▼
DETECTOR
   │
   ▼
TRACKER
   │
   ▼
POSITION ESTIMATOR
   │
   ▼
VALIDATION
   │
   ▼
VISION REPORT
   │
   ├── UI
   ├── SQLite
   └── WebSocket → Mobile
```

---

# 37. Camera stage

Responsabilidades:

```text
detectar cámaras
seleccionar dispositivo
abrir cámara
cerrar cámara
configurar resolución
configurar FPS
detectar errores
reconectar
entregar frames
```

OpenCV utilizará:

```text
cv2.VideoCapture
```

---

# 38. Preprocessing

Operaciones posibles:

```text
crop
resize
grayscale
HSV
threshold
denoise
normalize
perspective correction
ROI
```

---

# 39. Detector

Interfaz conceptual:

```python
class DetectorPort:
    def detect(self, frame):
        ...
```

Implementaciones:

```text
OpenCvHookDetector
OnnxHookDetector
```

---

# 40. Position Estimator

Responsabilidad:

```text
detección en píxeles
      ↓
calibración/geometría
      ↓
coordenadas físicas
```

Salida:

```text
PositionEstimate
```

con:

```text
x
y
z
confidence
timestamp
angle?
```

---

# 41. VisionReport

Ejemplo:

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.report",
  "messageId": "UUID",
  "timestamp": "2026-10-06T00:00:00-04:00",
  "payload": {
    "detected": true,
    "object": "gancho",
    "position": {
      "x": 145.2,
      "y": null,
      "z": 78.4,
      "angle": null
    },
    "confidence": 0.96
  }
}
```

Los valores no validados podrán ser:

```text
null
```

Nunca se fabricarán coordenadas.

---

# 42. Comunicación con la aplicación móvil

```text
BLANQUITA VISION
Laptop
192.168.x.x
        │
        │ WebSocket
        ▼
ws://IP_LAPTOP:8765/vision
        ▲
        │
BLANQUITA MOBILE
```

La laptop será servidor.

El móvil será cliente.

---

# 43. Tipos de mensajes

Laptop → Mobile:

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

---

# 44. Restricción crítica

BLANQUITA Vision NO enviará directamente:

```text
a
d
w
s
x
z
j
q
e
+
-
```

al ESP32.

Flujo correcto:

```text
VisionReport
    ↓
Mobile
    ↓
AutomationCoordinator
    ↓
SafetyGate
    ↓
MachineController
    ↓
ESP32
```

---

# 45. Concurrencia

La UI no debe ejecutar procesamiento pesado.

Arquitectura recomendada:

```text
┌───────────────────────────────┐
│ MAIN THREAD                   │
│ PySide6 / UI                  │
└──────────────┬────────────────┘
               │
       ┌───────┼────────┬─────────────┐
       │       │        │             │
       ▼       ▼        ▼             ▼
 CAMERA    VISION    NETWORK      STORAGE
 WORKER    WORKER    WORKER       WORKER
```

---

# 46. Threads y procesos

Primera implementación:

```text
threads/workers Qt
```

No se introducirá `multiprocessing` hasta medir una necesidad real.

---

# 47. Estructura propuesta del proyecto

```text
blanquita_vision/
│
├── .python-version
├── .gitignore
├── pyproject.toml
├── uv.lock
├── README.md
│
├── src/
│   └── blanquita_vision/
│       │
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── domain/
│       │   ├── models/
│       │   └── ports/
│       │
│       ├── application/
│       │
│       ├── adapters/
│       │   ├── camera/
│       │   ├── detection/
│       │   ├── network/
│       │   └── storage/
│       │
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── logging.py
│       │   └── health.py
│       │
│       └── presentation/
│           ├── main_window.py
│           ├── screens/
│           │   ├── live_screen.py
│           │   ├── detection_screen.py
│           │   ├── calibration_screen.py
│           │   ├── analytics_screen.py
│           │   ├── reports_screen.py
│           │   ├── diagnostics_screen.py
│           │   └── settings_screen.py
│           └── widgets/
│
├── models/
├── calibration/
│
├── data/
│   ├── captures/
│   ├── reports/
│   └── blanquita_vision.db
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

# 48. Estrategia de desarrollo

## Fase 0 — entorno reproducible

```text
Python 3.13.16
uv
.venv
pyproject.toml
uv.lock
```

## Fase 1 — shell de aplicación

```text
PySide6
+
PyQtGraph
+
navegación
+
pantallas vacías
```

## Fase 2 — cámara

```text
cámara USB
↓
OpenCV
↓
NumPy
↓
PyQtGraph
↓
video en vivo
```

## Fase 3 — calibración

```text
imagen
↓
referencias
↓
calibración
↓
guardar perfil
```

## Fase 4 — detección del gancho

Primero:

```text
OpenCV clásico
```

## Fase 5 — PositionEstimate

```text
X
Y
Z
confidence
timestamp
angle?
```

## Fase 6 — WebSocket

```text
Laptop server
↕
Mobile client
```

Puerto:

```text
8765
```

Ruta:

```text
/vision
```

## Fase 7 — persistencia

```text
SQLite
+
capturas puntuales
```

## Fase 8 — ML / ONNX

Primero:

```text
onnxruntime CPU
```

Después:

```text
RTX 4050
+
onnxruntime-gpu
```

## Fase 9 — analítica

```text
PyQtGraph
+
SQLite
+
Polars si es necesario
```

## Fase 10 — distribución

```text
BLANQUITA_VISION.exe
```

---

# 49. Testing

La arquitectura debe permitir:

```text
FakeCamera
FakeDetector
FakeMobileClient
InMemoryRepository
```

Pruebas principales:

```text
frame → detection
detection → position
position → report
report → JSON
WebSocket → connect/disconnect
invalid report → rejected
camera failure → state error
database persistence
calibration load/save
```

---

# 50. Métricas

El programa debe medir desde el principio:

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

---

# 51. Diseño visual

La aplicación tendrá un enfoque:

> **Consola industrial/técnica de visión.**

Características:

- Interfaz oscura.
- Alto contraste.
- Video como elemento central.
- Estados claramente visibles.
- Paneles de diagnóstico.
- Métricas en tiempo real.
- Jerarquía visual simple.
- Prioridad a legibilidad y respuesta.

Tecnologías:

```text
PySide6 Qt Widgets
PyQtGraph
```

---

# 52. Restricciones

BLANQUITA Vision no debe:

- Controlar directamente al ESP32.
- Enviar comandos de motores.
- Inventar coordenadas no medibles.
- Bloquear la UI con procesamiento.
- Acoplarse rígidamente a una única cámara.
- Acoplar el dominio a OpenCV.
- Depender obligatoriamente de GPU.
- Requerir Internet.
- Grabar video continuo en V1.
- Instalar múltiples variantes OpenCV simultáneamente.
- Actualizar dependencias automáticamente.

---

# 53. Compatibilidad con red BLANQUITA

```text
ROUTER
│
├── Laptop / BLANQUITA Vision
├── Móvil / BLANQUITA Mobile
└── ESP32 / Cartesiano
```

La laptop necesita comunicarse únicamente con la aplicación móvil.

---

# 54. Tolerancia a fallos

## Laptop sin móvil

```text
Visión continúa localmente
Reportes no producen acciones físicas
```

## Cámara desconectada

```text
VisionState = error
Reportes inválidos
Móvil informado
```

## Detector falla

```text
No se genera PositionEstimate válido
```

## GPU no disponible

```text
fallback CPU
```

## WebSocket cae

```text
Visor local continúa
Automatización móvil queda sin visión
```

---

# 55. Resultado esperado de V1

BLANQUITA Vision V1 deberá poder:

```text
1. Iniciar aplicación Windows.
2. Detectar/seleccionar cámara.
3. Mostrar video en vivo.
4. Ejecutar calibración.
5. Detectar el gancho.
6. Generar PositionEstimate.
7. Mostrar X/Y/Z disponibles.
8. Mostrar confidence.
9. Registrar timestamp.
10. Mostrar angle si el detector lo soporta.
11. Mostrar overlays.
12. Guardar capturas puntuales.
13. Persistir datos en SQLite.
14. Mostrar analítica básica.
15. Mostrar diagnósticos.
16. Ejecutar servidor WebSocket.
17. Enviar VisionReport al móvil.
18. Operar sin Internet.
19. No controlar directamente al ESP32.
20. Distribuirse como aplicación Windows `.exe`.
```

---

# 56. Baseline resumido

```text
WINDOWS 10 / 11 x64
│
└── Python 3.13.16
    │
    ├── ENVIRONMENT
    │   └── uv 0.12.22
    │
    ├── UI
    │   ├── PySide6 6.11.2
    │   └── PyQtGraph 0.14.0
    │
    ├── VISION
    │   ├── OpenCV Contrib Headless 4.14.0.94
    │   └── NumPy 2.5.3
    │
    ├── AI
    │   ├── ONNX Runtime 1.30.0
    │   └── ONNX Runtime GPU 1.30.0 (fase posterior)
    │
    ├── PROTOCOL
    │   ├── Pydantic 2.13.5
    │   └── JSON
    │
    ├── NETWORK
    │   └── websockets 17.1
    │
    ├── STORAGE
    │   └── SQLite / sqlite3
    │
    ├── ANALYTICS
    │   └── Polars 1.44.2
    │
    ├── TESTS
    │   └── pytest 9.1.1
    │
    └── DISTRIBUTION
        └── PyInstaller 6.22.3
```

---

# 57. Decisión arquitectónica definitiva

BLANQUITA Vision queda definido como:

> **Una aplicación desktop Windows de percepción visual, construida en Python con PySide6, OpenCV y una arquitectura Hexagonal / Ports & Adapters, cuya salida principal es un VisionReport estructurado enviado a BLANQUITA Mobile mediante WebSocket.**

Pipeline:

```text
CÁMARA
   ↓
CAPTURE
   ↓
PREPROCESS
   ↓
DETECTION
   ↓
TRACKING
   ↓
POSITION ESTIMATION
   ↓
VALIDATION
   ↓
VISION REPORT
   ↓
┌─────────────┬──────────────┐
│             │              │
UI          SQLite       WebSocket
                              │
                              ▼
                        BLANQUITA MOBILE
```

Separación final:

```text
BLANQUITA VISION
= PERCEPCIÓN

BLANQUITA MOBILE
= DECISIÓN / SUPERVISIÓN

ESP32
= EJECUCIÓN / PROTECCIÓN
```
