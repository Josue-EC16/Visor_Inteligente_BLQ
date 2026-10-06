# SPEC-01 — Pipeline de visión, calibración, detección y estimación de posición

## 1. Identificación

| Campo | Valor |
|---|---|
| SPEC ID | SPEC-01 |
| Nombre | Pipeline de visión, calibración, detección y estimación de posición |
| Archivo oficial | `SPEC-01_VISION_PIPELINE_CALIBRATION_DETECTION_POSITION.md` |
| Versión | 1.0.0 |
| Estado | APPROVED |
| Proyecto | BLANQUITA Vision |
| Plataforma | Windows 10 / Windows 11 x64 |
| Fecha | 2026-10-06 |
| Dependencia | SPEC-00 — VALIDATED |
| Specs relacionadas | SPEC-00, SPEC-02, SPEC-03 |

### 1.1. Fuentes normativas

1. `AGENTS.md`
2. `VISION_INTELIGENTE_BLQ.md`
3. `ARQUITECTURA_CONEXION.md`
4. `APP_MOVIL_BLANQ_V2.md`
5. `SPEC-00_FOUNDATION_ARCHITECTURE_UI_CAPTURE.md`
6. Decisiones explícitas aprobadas por el usuario para SPEC-01.

### 1.2. Actualización explícita de convención de ejes

La documentación base anterior utilizaba originalmente:

```text
X = horizontal
Y = profundidad
Z = altura
```

Para SPEC-01 el usuario autoriza expresamente sustituir esa convención por:

```text
X = horizontal: izquierda ↔ derecha
Y = vertical: abajo ↔ arriba
Z = profundidad
```

Esta convención deberá ser respetada por SPEC-02 y SPEC-03. No se modifican otros documentos automáticamente desde esta SPEC.

---

## 2. Contexto

SPEC-00 dejó implementados y validados `CameraPort`, `OpenCvCamera`, `Frame`, `LatestFrameStore`, Camera Worker, LIVE, shell PySide6, navegación y lifecycle de cámara.

SPEC-01 convierte esos frames en percepción estructurada:

```text
Frame
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
VisionObservation
```

El objetivo visual inicial es detectar directamente el **gancho celeste del robot cartesiano**, sin marcador ArUco ni otro marcador artificial.

La detección será mediante OpenCV clásico. ONNX permanece fuera de alcance hasta SPEC-03.

La cámara es monocular. Por tanto:

```text
X = estimable mediante homografía
Y = estimable mediante homografía
Z = null
```

La calibración V1 será una homografía planar definida mediante cuatro correspondencias manuales entre puntos de imagen y puntos físicos conocidos.

---

## 3. Objetivo

Implementar el pipeline de percepción clásica de BLANQUITA Vision para:

1. consumir frames de SPEC-00;
2. calibrar el plano de trabajo mediante cuatro puntos manuales;
3. detectar el gancho celeste con OpenCV clásico;
4. realizar tracking mediante CSRT;
5. volver a detectar cuando se pierda el tracking;
6. estimar X/Y mediante homografía;
7. mantener Z en `null` hasta contar con profundidad validada;
8. conservar posición raw y filtered;
9. suavizar mediante EMA;
10. producir `VisionObservation` interna;
11. mostrar overlays y estados de visión en UI;
12. medir precisión y rendimiento sin inventar objetivos numéricos;
13. mantener independencia respecto de ONNX, WebSocket, SQLite y control físico.

---

## 4. Alcance

### 4.1. IN SCOPE

- Vision Worker separado del hilo UI.
- Consumo de latest-frame.
- Preprocessing necesario para color/contornos.
- Procesamiento de toda la imagen.
- Conversión BGR → HSV.
- Segmentación configurable del color celeste.
- Morphology configurable cuando corresponda.
- Extracción y filtrado de contornos.
- Candidatos y selección de candidato principal.
- Bounding box y centroide.
- Confidence/quality score normalizado 0..1.
- `DetectorPort`.
- `OpenCvHookDetector`.
- Activación manual del detector.
- Tracking mediante CSRT.
- Redetección al perder tracking.
- `TrackerPort` y `TrackingResult`.
- Homografía de cuatro puntos manuales.
- `Calibration`, `CalibrationPoint` y `CalibrationStatus`.
- `CalibrationRepositoryPort`.
- `InMemoryCalibrationRepository`.
- Invalidación por cambios geométricos relevantes.
- `PositionEstimatorPort`.
- `HomographyPositionEstimator`.
- X/Y físicos.
- Z = `null`.
- raw_position y filtered_position.
- EMA configurable.
- `PositionEstimate`.
- `VisionObservation`.
- CALIBRACIÓN funcional.
- DETECCIÓN funcional.
- LIVE ampliado con overlays.
- Métricas inmediatas del pipeline.
- Tests unitarios, integración, negativos, hardware y precisión.

### 4.2. OUT OF SCOPE

- marcador ArUco en el gancho;
- marcador artificial de color;
- calibración intrínseca completa con chessboard;
- reconstrucción 3D;
- estimación métrica de Z;
- cámara estéreo;
- sensor de profundidad;
- detector ONNX;
- entrenamiento ML;
- dataset ML;
- inferencia GPU;
- persistencia SQLite;
- almacenamiento persistente de calibración;
- historial de detecciones;
- almacenamiento de capturas;
- WebSocket;
- protocolo JSON final;
- `VisionReport` de red;
- conexión con Mobile;
- conexión con ESP32;
- comandos de movimiento;
- analítica histórica;
- reportes históricos;
- empaquetado `.exe`.

---

## 5. Actores

### 5.1. Usuario operador

Puede calibrar, configurar detector, iniciar/detener percepción, invalidar/recalibrar y observar resultados.

### 5.2. Cámara

Fuente de frames ya abstraída por SPEC-00.

### 5.3. Vision Pipeline

Coordina preprocessing, detector, tracker, estimación, filtrado y validación.

### 5.4. OpenCvHookDetector

Adapter de detección clásica del gancho celeste.

### 5.5. CSRT Tracker

Seguimiento temporal del objeto detectado.

### 5.6. Calibration Service

Gestiona creación, validación, activación e invalidación de calibraciones.

### 5.7. Position Estimator

Transforma posición en imagen a X/Y físicos.

### 5.8. SPEC-02

Consumidor futuro de `VisionObservation` para protocolo, persistencia, analítica, reportes y diagnósticos.

---

## 6. Casos de uso

### UC-01-01 — Iniciar detector

**Actor:** Usuario operador.

**Precondiciones:** cámara STREAMING, frame válido, detector detenido.

**Trigger:** `Iniciar detector`.

**Flujo principal:**

1. Validar cámara.
2. Iniciar Vision Worker.
3. Consumir latest frame.
4. Preprocesar.
5. Detectar gancho.
6. Si hay detección válida, inicializar CSRT.
7. Si hay calibración válida, estimar X/Y.
8. Aplicar EMA cuando corresponda.
9. Generar `VisionObservation`.
10. Actualizar UI.

**Alternativo:** sin calibración, la detección funciona solo en espacio de imagen.

**Errores:** cámara no streaming, parámetros inválidos, OpenCV/worker error.

### UC-01-02 — Detener detector

**Actor:** Usuario.

**Trigger:** `Detener detector`.

**Flujo:** cancelar Vision Worker, liberar tracker, pasar a STOPPED, limpiar/invalidar overlays actuales.

### UC-01-03 — Configurar detector

**Actor:** Usuario.

**Parámetros:** rangos HSV, área mínima, área máxima opcional, morphology, confidence mínima y demás parámetros estrictamente necesarios.

**Regla:** valores definitivos se obtienen mediante pruebas físicas; no se inventan como baseline.

### UC-01-04 — Detectar gancho celeste

1. Frame BGR válido.
2. Convertir a HSV.
3. Crear máscara.
4. Limpiar máscara si morphology está activa.
5. Extraer contornos.
6. Filtrar candidatos.
7. Calcular geometría.
8. Calcular score.
9. Seleccionar candidato válido.
10. Generar `Detection`.

Si no hay candidato válido: `detected = false`.

### UC-01-05 — Inicializar tracking

**Precondición:** Detection válida.

1. Crear tracker CSRT.
2. Inicializar con frame y bounding box.
3. Pasar a TRACKING si tiene éxito.

### UC-01-06 — Mantener tracking

1. Actualizar CSRT con nuevo frame.
2. Validar bounding box.
3. Obtener centro.
4. Generar `TrackingResult`.

Si falla, pasar a LOST/SEARCHING.

### UC-01-07 — Reacquirir objeto

1. Descartar tracker inválido.
2. Volver a `OpenCvHookDetector`.
3. Si reaparece candidato válido, reinicializar CSRT.
4. Si no, continuar SEARCHING.

### UC-01-08 — Crear calibración planar

**Actor:** Usuario.

1. Obtener frame de referencia consistente.
2. Registrar cuatro correspondencias.
3. Cada correspondencia incluye `(u,v)` y `(X,Y)` conocidos.
4. Validar pares completos y no degenerados.
5. Calcular homografía.
6. Validar matriz.
7. Calcular error interno de reproyección cuando corresponda.
8. Crear `Calibration`.
9. Aplicar en sesión.
10. Guardar únicamente en memoria.

### UC-01-09 — Invalidar calibración

Se invalida ante:

- cambio de cámara;
- cambio de resolución efectiva;
- movimiento físico reportado de cámara/referencias;
- acción manual `Invalidar/Recalibrar`.

Una reconexión equivalente de misma cámara y resolución no invalida por sí sola.

### UC-01-10 — Estimar X/Y

1. Obtener `(u,v)` del centro/punto visual.
2. Aplicar homografía.
3. Obtener X/Y.
4. Validar finitud.
5. Establecer `Z = null`.
6. Generar raw_position.
7. Aplicar EMA.
8. Generar filtered_position.

### UC-01-11 — Detectar sin calibración

La detección/tracking puede continuar, pero X/Y/Z físicos quedan no disponibles.

### UC-01-12 — Suavizar posición

```text
filtered_t = alpha * raw_t + (1-alpha) * filtered_(t-1)
```

Con `0 < alpha <= 1`.

Alpha operativo: TBD mediante pruebas físicas.

### UC-01-13 — Mostrar percepción en LIVE

Mostrar cuando corresponda:

- bounding box;
- centro;
- estado detector;
- estado tracker;
- estado calibración;
- X/Y raw;
- X/Y filtered;
- Z no disponible;
- confidence;
- timestamp;
- tiempo de procesamiento.

### UC-01-14 — Validar precisión física

1. Posicionar gancho en puntos físicos conocidos.
2. Registrar referencia real.
3. Capturar estimación.
4. Calcular error X, error Y y error 2D.
5. Resumir MAE/error máximo.
6. Documentar resultados.

No existe umbral numérico aprobado todavía.

---

## 7. Requisitos funcionales

### Pipeline

**RF-01-001** El sistema deberá consumir frames válidos de SPEC-00.

**RF-01-002** El pipeline deberá ejecutarse fuera del hilo principal de UI.

**RF-01-003** El pipeline deberá priorizar latest-frame y evitar colas ilimitadas.

**RF-01-004** El usuario deberá iniciar manualmente el detector.

**RF-01-005** El usuario deberá poder detener el detector.

**RF-01-006** Un detector detenido no deberá continuar procesando frames.

### Preprocessing

**RF-01-007** El procesamiento inicial deberá utilizar la imagen completa.

**RF-01-008** El sistema deberá preservar las coordenadas del frame fuente.

**RF-01-009** Toda transformación geométrica interna deberá poder mapear resultados de vuelta a coordenadas fuente.

**RF-01-010** El preprocessing deberá soportar BGR → HSV.

**RF-01-011** Deberá soportar operaciones morfológicas configurables cuando se necesiten.

### Detección

**RF-01-012** El dominio deberá definir `DetectorPort`.

**RF-01-013** La implementación inicial será `OpenCvHookDetector`.

**RF-01-014** El detector deberá localizar directamente el gancho físico celeste sin marcador artificial.

**RF-01-015** La detección deberá basarse inicialmente en segmentación de color y contornos.

**RF-01-016** Los rangos HSV deberán ser configurables.

**RF-01-017** Los valores HSV definitivos deberán validarse con hardware real.

**RF-01-018** El detector deberá permitir restricciones geométricas configurables.

**RF-01-019** El detector podrá producir múltiples candidatos internos.

**RF-01-020** Deberá seleccionar un candidato principal solo cuando cumpla validación.

**RF-01-021** Una detección válida deberá incluir bounding box.

**RF-01-022** Una detección válida deberá incluir centro/punto visual en píxeles.

**RF-01-023** Una detección deberá incluir timestamp asociado al frame.

**RF-01-024** `confidence` deberá estar normalizado en `[0,1]`.

**RF-01-025** `confidence` deberá representar score de calidad, no probabilidad estadística.

**RF-01-026** El score deberá documentar los factores utilizados.

**RF-01-027** El umbral mínimo deberá ser configurable.

**RF-01-028** El valor operativo del umbral permanecerá TBD hasta pruebas físicas.

### Tracking

**RF-01-029** El sistema deberá utilizar CSRT como tracker inicial.

**RF-01-030** CSRT deberá inicializarse desde Detection válida.

**RF-01-031** El tracker no deberá sustituir permanentemente al detector.

**RF-01-032** Si CSRT pierde el objeto, el sistema deberá volver a detección.

**RF-01-033** Una redetección válida deberá poder reinicializar CSRT.

**RF-01-034** La pérdida de tracking no deberá cerrar la cámara ni la aplicación.

### Calibración

**RF-01-035** La calibración principal será homografía planar.

**RF-01-036** Utilizará exactamente cuatro correspondencias manuales en V1.

**RF-01-037** Cada correspondencia tendrá `(u,v)` de imagen y `(X,Y)` físicos conocidos.

**RF-01-038** El sistema no impondrá un origen físico arbitrario; las coordenadas físicas se proporcionarán explícitamente.

**RF-01-039** Los cuatro puntos deberán ser distintos.

**RF-01-040** Configuraciones degeneradas deberán ser rechazadas.

**RF-01-041** Se deberá calcular matriz de homografía imagen → plano físico.

**RF-01-042** La matriz deberá validarse numéricamente antes de activarse.

**RF-01-043** CALIBRACIÓN deberá mostrar estado actual.

**RF-01-044** CALIBRACIÓN deberá permitir crear una nueva calibración.

**RF-01-045** CALIBRACIÓN deberá permitir invalidar la calibración activa.

**RF-01-046** Cambiar cámara deberá invalidar la calibración.

**RF-01-047** Cambiar resolución efectiva deberá invalidar la calibración.

**RF-01-048** El usuario deberá recalibrar cuando la cámara cambie físicamente de posición/orientación.

**RF-01-049** Reconectar la misma cámara con igual resolución no invalidará automáticamente por sí solo.

**RF-01-050** La calibración activa se mantendrá en memoria.

**RF-01-051** Se deberá definir `CalibrationRepositoryPort`.

**RF-01-052** Se deberá implementar `InMemoryCalibrationRepository`.

**RF-01-053** SPEC-01 no deberá persistir calibración en SQLite/filesystem.

### Coordenadas y estimación

**RF-01-054** La convención será X horizontal, Y vertical, Z profundidad.

**RF-01-055** Sentidos positivos y origen físico deberán provenir de la calibración y no de suposiciones internas.

**RF-01-056** La homografía estimará X/Y.

**RF-01-057** SPEC-01 producirá `Z = null`.

**RF-01-058** No se deberá inferir Z mediante heurísticos no validados.

**RF-01-059** Se deberá definir `PositionEstimatorPort`.

**RF-01-060** La implementación inicial será `HomographyPositionEstimator`.

**RF-01-061** El estimador requerirá punto de imagen y calibración válida.

**RF-01-062** El estimador transformará `(u,v)` a `(X,Y)`.

**RF-01-063** Resultados no finitos deberán rechazarse.

**RF-01-064** Sin calibración válida, no se mostrarán coordenadas físicas como válidas.

### Suavizado

**RF-01-065** `PositionEstimate` conservará raw_position.

**RF-01-066** `PositionEstimate` conservará filtered_position.

**RF-01-067** El filtro inicial será EMA.

**RF-01-068** EMA se aplicará a cada eje disponible.

**RF-01-069** `alpha` será configurable.

**RF-01-070** El alpha recomendado permanecerá TBD hasta prueba física.

**RF-01-071** El estado EMA deberá reiniciarse cuando la trayectoria deje de ser continua por pérdida del objeto, según política cubierta por tests.

### Ángulo y observación

**RF-01-072** El modelo soportará `angle` nullable.

**RF-01-073** SPEC-01 utilizará `angle = null`.

**RF-01-074** La salida interna será `VisionObservation`.

**RF-01-075** `VisionObservation` podrá contener Detection, TrackingResult, PositionEstimate y estados.

**RF-01-076** SPEC-01 no serializará VisionObservation como protocolo final.

**RF-01-077** SPEC-02 deberá poder transformarla en VisionReport sin rediseñar el pipeline.

### UI

**RF-01-078** CALIBRACIÓN deberá convertirse en pantalla funcional.

**RF-01-079** DETECCIÓN deberá convertirse en pantalla funcional.

**RF-01-080** LIVE deberá mostrar overlays cuando visión esté activa.

**RF-01-081** LIVE deberá distinguir detector detenido, searching, detected, tracking y lost.

**RF-01-082** LIVE mostrará X/Y solo cuando sean físicamente válidos.

**RF-01-083** LIVE mostrará Z como `No disponible`, nunca como cero simulado.

**RF-01-084** La UI mostrará confidence como score de calidad.

---

## 8. Requisitos no funcionales

**RNF-01-001** Respetar Arquitectura Hexagonal + Ports & Adapters + Vision Pipeline.

**RNF-01-002** `domain/` no deberá importar `cv2` ni PySide6 para responsabilidades abstraídas.

**RNF-01-003** `OpenCvHookDetector` quedará detrás de `DetectorPort`.

**RNF-01-004** `HomographyPositionEstimator` quedará detrás de `PositionEstimatorPort`.

**RNF-01-005** La calibración no dependerá de SQLite.

**RNF-01-006** La arquitectura permitirá añadir `OnnxHookDetector` en SPEC-03 sin reemplazar el pipeline.

**RNF-01-007** Detección, tracking y posición no se ejecutarán en UI thread.

**RNF-01-008** La UI deberá permanecer interactiva durante percepción.

**RNF-01-009** Se mantendrá semántica latest-frame para evitar latencia acumulativa.

**RNF-01-010** FPS objetivo = TBD mediante benchmark.

**RNF-01-011** Latencia objetivo = TBD mediante benchmark.

**RNF-01-012** Medir FPS pipeline y tiempos de preprocessing, detection, tracking, position y total.

**RNF-01-013** No declarar precisión métrica sin prueba física.

**RNF-01-014** Medir precisión X/Y experimentalmente.

**RNF-01-015** No declarar precisión de Z porque Z no se estima.

**RNF-01-016** Error del detector no deberá cerrar cámara.

**RNF-01-017** Error/pérdida de tracking deberá degradar a redetección.

**RNF-01-018** Calibración inválida deshabilitará posición física, no necesariamente detección.

**RNF-01-019** Resultados NaN/Inf deberán rechazarse.

**RNF-01-020** Pipeline deberá poder probarse con fixtures sin hardware.

**RNF-01-021** Detector deberá poder sustituirse por FakeDetector.

**RNF-01-022** Estimador deberá poder sustituirse por FakePositionEstimator.

**RNF-01-023** Calibración deberá probarse con datos sintéticos conocidos.

**RNF-01-024** Identificadores de código en inglés.

**RNF-01-025** UI/documentación visible en español.

**RNF-01-026** No añadir dependencia nueva si NumPy/OpenCV aprobados son suficientes.

**RNF-01-027** Ningún resultado de SPEC-01 se convertirá directamente en comando de movimiento.

**RNF-01-028** Coordenadas antiguas no podrán presentarse como actuales tras pérdida del objeto.

---

## 9. Reglas de negocio / dominio

**BR-01-001** El objetivo visual V1 es el gancho físico celeste.

**BR-01-002** No se utilizará marcador artificial en el gancho.

**BR-01-003** OpenCV clásico es el detector productivo de SPEC-01.

**BR-01-004** `X = horizontal`, `Y = vertical`, `Z = profundidad`.

**BR-01-005** Z permanecerá `null` hasta una metodología aprobada y validada.

**BR-01-006** Detección/tracking pueden funcionar sin calibración; posición física no.

**BR-01-007** La homografía representa mapeo 2D del plano, no reconstrucción 3D.

**BR-01-008** Confidence es score normalizado, no probabilidad estadística.

**BR-01-009** El filtrado no destruye raw_position.

**BR-01-010** Pérdida de tracking degrada a redetección.

**BR-01-011** Calibración solo es válida mientras las condiciones geométricas permanezcan válidas.

**BR-01-012** Calibración vive en memoria durante SPEC-01.

**BR-01-013** VisionObservation es observación, no autorización física.

---

## 10. Modelo de estados

### 10.1. VisionPipelineState

```text
STOPPED
STARTING
RUNNING
STOPPING
ERROR
```

```text
STOPPED --start--> STARTING --success--> RUNNING
RUNNING --stop--> STOPPING --> STOPPED
STARTING --failure--> ERROR
RUNNING --fatal error--> ERROR
ERROR --reset/stop--> STOPPED
```

### 10.2. DetectionState

```text
DISABLED
SEARCHING
DETECTED
NOT_DETECTED
ERROR
```

### 10.3. TrackingState

```text
INACTIVE
INITIALIZING
TRACKING
LOST
ERROR
```

```text
INACTIVE --valid detection--> INITIALIZING --success--> TRACKING
TRACKING --update fails--> LOST --redetection--> INITIALIZING
```

### 10.4. CalibrationStatus

```text
UNCALIBRATED
CALIBRATING
VALID
INVALID
ERROR
```

### 10.5. PositionStatus

```text
UNAVAILABLE
RAW_AVAILABLE
FILTERED_AVAILABLE
INVALID
```

---

## 11. Modelo de datos

### 11.1. ImagePoint

```text
u: float
v: float
```

Coordenadas en píxeles del frame fuente.

### 11.2. PhysicalPoint2D

```text
x: float
y: float
unit: str
```

La unidad deberá ser consistente dentro de la calibración.

### 11.3. CalibrationPoint

```text
image: ImagePoint
physical: PhysicalPoint2D
```

### 11.4. Calibration

```text
id: str
camera_id: str
width: int
height: int
points: 4 CalibrationPoint
homography: Matrix3x3
unit: str
created_at: datetime
status: CalibrationStatus
internal_reprojection_error: float?
```

El error interno no equivale a precisión física independiente.

### 11.5. DetectionParameters

```text
hue_min: int
hue_max: int
saturation_min: int
saturation_max: int
value_min: int
value_max: int
min_area: float
max_area: float?
morphology_enabled: bool
morphology_kernel_size: int?
minimum_confidence: float
```

Los valores concretos de tuning deberán obtenerse mediante hardware real.

### 11.6. DetectionCandidate

```text
bounding_box: BoundingBox
centroid: ImagePoint
contour_area: float
mask_coverage: float?
geometry_score: float?
color_score: float?
temporal_score: float?
confidence: float
```

### 11.7. Detection

```text
detected: bool
object_name: str
bounding_box: BoundingBox?
centroid: ImagePoint?
confidence: float
timestamp: datetime
frame_sequence: int
```

`object_name = "gancho"`.

### 11.8. TrackingResult

```text
state: TrackingState
bounding_box: BoundingBox?
centroid: ImagePoint?
source: str
timestamp: datetime
```

`source` deberá distinguir `detection` y `csrt`.

### 11.9. SpatialPosition

```text
x: float?
y: float?
z: float?
unit: str?
```

Con calibración válida en SPEC-01:

```text
x != null
y != null
z = null
```

### 11.10. PositionEstimate

```text
raw_position: SpatialPosition
filtered_position: SpatialPosition
confidence: float
timestamp: datetime
angle: float?
calibrated: bool
```

Para SPEC-01: `angle = null`.

### 11.11. EmaFilterState

```text
alpha: float
initialized: bool
last_x: float?
last_y: float?
```

`0 < alpha <= 1`.

### 11.12. VisionObservation

```text
frame_sequence: int
timestamp: datetime
detection: Detection?
tracking: TrackingResult?
position: PositionEstimate?
calibration_status: CalibrationStatus
pipeline_state: VisionPipelineState
processing_time_ms: float?
```

Modelo interno. No es el protocolo de red.

---

## 12. Interfaces / Ports

### 12.1. DetectorPort

```python
class DetectorPort(Protocol):
    def detect(self, frame: "Frame", parameters: "DetectionParameters") -> "Detection":
        ...
```

No conoce UI, WebSocket ni posición física.

### 12.2. TrackerPort

```python
class TrackerPort(Protocol):
    def initialize(self, frame: "Frame", box: "BoundingBox") -> None:
        ...

    def update(self, frame: "Frame") -> "TrackingResult":
        ...

    def reset(self) -> None:
        ...
```

### 12.3. PositionEstimatorPort

```python
class PositionEstimatorPort(Protocol):
    def estimate(self, image_point: "ImagePoint", calibration: "Calibration") -> "SpatialPosition":
        ...
```

### 12.4. CalibrationRepositoryPort

```python
class CalibrationRepositoryPort(Protocol):
    def get_active(self) -> "Calibration | None":
        ...

    def set_active(self, calibration: "Calibration") -> None:
        ...

    def invalidate(self) -> None:
        ...
```

### 12.5. Position filter

Contrato conceptual:

```text
update(raw_position) -> filtered_position
reset()
```

---

## 13. Adapters

### 13.1. OpenCvHookDetector

```text
DetectorPort
   ↓
OpenCvHookDetector
   ↓
OpenCV
```

Pipeline:

```text
BGR
 ↓
HSV
 ↓
inRange
 ↓
morphology opcional
 ↓
findContours
 ↓
filtrado
 ↓
scoring
 ↓
Detection
```

### 13.2. CsrtTracker

Encapsula CSRT. La implementación deberá usar la variante disponible del OpenCV aprobado y reportar explícitamente si CSRT no está disponible.

### 13.3. HomographyPositionEstimator

Aplica la matriz de calibración para convertir `(u,v)` en X/Y.

### 13.4. InMemoryCalibrationRepository

Mantiene 0 o 1 calibración activa. No persiste.

### 13.5. EmaPositionFilter

Implementación local sin nueva dependencia.

---

## 14. Flujo técnico

### 14.1. Pipeline general

```text
Camera Worker (SPEC-00)
        ↓
LatestFrameStore
        ↓
Vision Worker
        ↓
Preprocess
        ↓
OpenCvHookDetector
        ↓
CSRT / redetection
        ↓
ImagePoint
        ↓
HomographyPositionEstimator
        ↓
Raw X/Y, Z=null
        ↓
EMA
        ↓
Filtered X/Y, Z=null
        ↓
VisionObservation
        ↓
Presentation
```

### 14.2. Sin calibración

```text
Frame → Detection → Tracking → pixel position → physical unavailable
```

### 14.3. Reacquisición

```text
TRACKING
  ↓ fail
LOST
  ↓
OpenCvHookDetector
  ↓ found
CSRT initialize
  ↓
TRACKING
```

---

## 15. Concurrencia

### 15.1. UI Thread

Responsable de renderizado, navegación e interacción.

No ejecutará continuamente `cvtColor`, threshold, contours, CSRT ni homografía.

### 15.2. Camera Worker

Permanece responsabilidad de SPEC-00 y no deberá rediseñarse.

### 15.3. Vision Worker

Responsable de preprocessing, detection, tracking, position, EMA, VisionObservation y métricas del pipeline.

### 15.4. Backpressure

Si Camera Worker produce más rápido que Vision Worker, se procesa el frame más reciente y se descartan intermedios obsoletos.

### 15.5. Ownership

- Camera Worker posee la captura.
- Vision Worker posee el tracker activo.
- UI no manipula objetos OpenCV activos.
- Calibration se consulta mediante servicio/port.

### 15.6. Cancelación

Debe cancelarse ante detener detector, shutdown, cámara no utilizable o error fatal del Vision Worker.

Detener detector no implica desconectar cámara.

---

## 16. Manejo de errores

| Error | Detección | Reacción | Recuperación | Estado | Log |
|---|---|---|---|---|---|
| Cámara no streaming | precondición | rechazar inicio | conectar cámara | STOPPED | WARNING |
| Frame inválido | validación | omitir | esperar siguiente | RUNNING | WARNING |
| HSV inválido | validación config | rechazar | corregir | previo/ERROR | WARNING |
| Cero candidatos | detector | not_detected | seguir buscando | SEARCHING | INFO/debug |
| Candidatos ambiguos | validation | no afirmar detección | ajustar/siguiente frame | SEARCHING | WARNING si persistente |
| CSRT no disponible | capability check | no iniciar tracking | corrección técnica | ERROR | ERROR |
| CSRT pierde objeto | update falla | reset | redetectar | LOST/SEARCHING | INFO |
| Homografía degenerada | validación | rechazar | recalibrar | UNCALIBRATED/ERROR | ERROR |
| Homografía no finita | check numérico | rechazar posición | recalibrar | INVALID | ERROR |
| Cambio de cámara | comparación | invalidar calibration | recalibrar | INVALID | WARNING |
| Cambio resolución | comparación | invalidar | recalibrar | INVALID | WARNING |
| Cámara movida | acción operador | invalidar | recalibrar | INVALID | WARNING |
| Sin calibración | estado | no físico | calibrar | UNAVAILABLE | INFO |
| Alpha inválido | validación | rechazar | corregir | raw disponible | WARNING |
| Excepción worker | boundary | detener pipeline | restart manual | ERROR | ERROR |

Regla: datos antiguos no se mostrarán como medición actual tras pérdida del objeto.

---

## 17. Observabilidad

### 17.1. Eventos

```text
vision_pipeline_started
vision_pipeline_stopped
detector_started
detector_stopped
hook_detected
hook_lost
tracker_initialized
tracker_lost
tracker_reinitialized
calibration_started
calibration_created
calibration_invalidated
calibration_error
position_available
position_unavailable
vision_pipeline_error
```

No registrar cada frame a nivel INFO.

### 17.2. Métricas inmediatas

- pipeline FPS;
- preprocess ms;
- detection ms;
- tracking ms;
- position ms;
- filter ms;
- total pipeline ms;
- confidence;
- detections;
- lost tracking;
- reacquisitions;
- raw X/Y;
- filtered X/Y.

Persistencia histórica pertenece a SPEC-02.

---

## 18. UI/UX

### 18.1. Diseño

Mantener diseño negro, técnico y de alto contraste de SPEC-00.

### 18.2. CALIBRACIÓN

Debe incluir:

- estado;
- cámara asociada;
- resolución;
- frame de referencia;
- selección P1-P4;
- campos X/Y por punto;
- unidad declarada;
- calcular;
- validar;
- aplicar;
- invalidar;
- recalibrar;
- error interno con advertencia de interpretación.

Estados:

```text
Sin calibrar
Marcando puntos
Calculando
Válida
Inválida
Error
```

### 18.3. DETECCIÓN

Debe incluir:

- detector ON/OFF;
- estado;
- parámetros HSV;
- restricciones geométricas;
- confidence actual;
- tracking state;
- bounding box;
- centro en píxeles;
- X/Y raw;
- X/Y filtered;
- Z: No disponible;
- alpha EMA;
- estado de calibración.

No debe incorporar selector ONNX funcional.

### 18.4. LIVE

Overlays:

```text
bounding box
centro
"gancho"
confidence
tracking state
X/Y cuando sean válidos
Z no disponible
```

Los estados deberán distinguirse también con texto, no solo color.

---

## 19. Seguridad

- SPEC-01 no controla ESP32.
- No genera comandos de motor.
- `VisionObservation` no es autorización.
- Coordenada no disponible se representa como `null`, no cero ficticio.
- Calibración inválida no podrá seguir produciendo posición física silenciosamente.
- Confidence alto no autoriza movimiento.
- Evitar buffers ilimitados, loops de redetección bloqueantes y creación descontrolada de trackers.

---

## 20. Persistencia

SPEC-01 solo mantiene en memoria:

```text
Calibration activa
estado detector
estado tracker
estado EMA
VisionObservation actual
```

No define tablas SQLite ni archivos persistentes de calibración.

SPEC-02 implementará persistencia futura.

---

## 21. Testing obligatorio

### TC-01-001 — Pipeline no inicia sin cámara
Resultado: rechazo controlado. Tipo: negative/integration.

### TC-01-002 — Inicio manual
Resultado: STOPPED → STARTING → RUNNING. Tipo: integration.

### TC-01-003 — Detener sin cerrar cámara
Resultado: pipeline STOPPED, cámara sigue bajo SPEC-00. Tipo: integration.

### TC-01-004 — Gancho celeste en fixture
Resultado: candidato detectado. Tipo: unit.

### TC-01-005 — Frame sin gancho
Resultado: detected=false. Tipo: negative.

### TC-01-006 — Múltiples objetos celestes
Resultado: scoring/validación evita candidato inválido. Tipo: edge case.

### TC-01-007 — HSV inválido
Resultado: configuración rechazada. Tipo: negative.

### TC-01-008 — Confidence en rango
Resultado: `0 <= confidence <= 1`. Tipo: unit.

### TC-01-009 — Confidence no es probabilidad
Resultado: modelo/UI lo representa como score de calidad. Tipo: UI/documentación.

### TC-01-010 — Inicializar CSRT
Resultado: TrackingState=TRACKING. Tipo: integration/OpenCV.

### TC-01-011 — Pérdida CSRT
Resultado: TRACKING → LOST/SEARCHING → detector. Tipo: integration.

### TC-01-012 — Reacquisición
Resultado: Detection nueva y CSRT reinicializado. Tipo: integration.

### TC-01-013 — Homografía sintética válida
Entrada: cuatro correspondencias con transformación conocida. Resultado: VALID. Tipo: unit.

### TC-01-014 — Puntos repetidos
Resultado: calibración rechazada. Tipo: negative.

### TC-01-015 — Configuración degenerada
Resultado: homografía no se activa. Tipo: negative.

### TC-01-016 — Transformación conocida
Resultado: X/Y sintéticos esperados dentro de tolerancia numérica del test. Tipo: unit.

La tolerancia sintética no equivale a precisión física.

### TC-01-017 — Z permanece null
Resultado: z is None. Tipo: unit.

### TC-01-018 — Sin calibración no hay posición física
Resultado: X/Y/Z no disponibles. Tipo: unit/integration.

### TC-01-019 — Cambio de cámara invalida calibración
Resultado: VALID → INVALID. Tipo: integration.

### TC-01-020 — Cambio de resolución invalida calibración
Resultado: VALID → INVALID. Tipo: unit/integration.

### TC-01-021 — Reconexión equivalente conserva calibración
Resultado: misma cámara/resolución no invalida por sí sola. Tipo: integration.

### TC-01-022 — Invalidación manual
Resultado: INVALID y posición física deshabilitada. Tipo: integration.

### TC-01-023 — EMA primer valor
Resultado: filtered se inicializa sin histórico inventado. Tipo: unit.

### TC-01-024 — EMA secuencia
Entrada: alpha conocido de test. Resultado: cálculo esperado. Tipo: unit.

### TC-01-025 — Alpha inválido
Resultado: rechazado. Tipo: negative.

### TC-01-026 — Raw se conserva
Resultado: raw y filtered diferenciables. Tipo: unit.

### TC-01-027 — Backpressure de visión
Entrada: productor más rápido. Resultado: latest-frame sin cola creciente. Tipo: performance/integration.

### TC-01-028 — Error detector no congela UI
Resultado: pipeline ERROR, UI operativa. Tipo: negative integration.

### TC-01-029 — VisionObservation interna
Resultado: modelo interno completo sin JSON/WebSocket. Tipo: unit.

### TC-01-030 — Sin dependencia ONNX productiva
Resultado: SPEC-01 funciona sin OnnxHookDetector. Tipo: architecture.

### TC-01-031 — Detección con hardware real

**Objetivo:** validar gancho físico celeste bajo entorno real.

**Procedimiento:** conectar cámara, iniciar detector, mover gancho, observar detecciones, registrar falsos positivos/falsos negativos.

**Tipo:** TEST CON HARDWARE REAL.

**Estado inicial:** TEST PENDIENTE.

### TC-01-032 — Tracking físico

Mover gancho en trayectorias representativas y verificar CSRT + redetección.

**Tipo:** TEST CON HARDWARE REAL.

**Estado inicial:** TEST PENDIENTE.

### TC-01-033 — Calibración física de cuatro puntos

1. definir cuatro puntos físicos conocidos;
2. registrar correspondencias;
3. calcular homografía;
4. probar puntos adicionales no usados en calibración.

**Tipo:** TEST CON HARDWARE REAL.

**Estado inicial:** TEST PENDIENTE.

### TC-01-034 — Benchmark de precisión X/Y

```text
error_x_i = |x_est_i - x_real_i|
error_y_i = |y_est_i - y_real_i|
error_2d_i = sqrt((x_est_i-x_real_i)^2 + (y_est_i-y_real_i)^2)
```

Calcular MAE X, MAE Y, error 2D medio y error máximo.

Umbral de aceptación: TBD.

**Tipo:** HARDWARE / ACCURACY.

### TC-01-035 — Benchmark de pipeline

Medir FPS pipeline, preprocess, detection, tracking, position, total y frames obsoletos descartados.

**Tipo:** performance.

### TC-01-036 — Movimiento físico de cámara

Tras calibrar, mover cámara, invalidar/recalibrar manualmente y verificar que X/Y anteriores dejan de mostrarse como válidos.

**Tipo:** TEST CON HARDWARE REAL.

---

## 22. Criterios de aceptación

**AC-01-001** DADO cámara STREAMING, CUANDO se inicia detector, ENTONCES el pipeline se ejecuta fuera del UI thread.

**AC-01-002** DADO gancho celeste visible y parámetros ajustados, CUANDO procesa OpenCV, ENTONCES puede producir Detection sin ONNX.

**AC-01-003** DADO Detection válida, CUANDO se inicializa CSRT, ENTONCES se intenta continuidad temporal.

**AC-01-004** DADO tracking activo, CUANDO CSRT pierde el objeto, ENTONCES se vuelve a detección.

**AC-01-005** DADO cuatro correspondencias no degeneradas, CUANDO se calcula calibración, ENTONCES se obtiene homografía válida o error explícito.

**AC-01-006** DADO Calibration válida, CUANDO existe punto visual válido, ENTONCES se producen X/Y físicos.

**AC-01-007** DADA cualquier estimación SPEC-01, CUANDO se consulta profundidad, ENTONCES Z es null/no disponible.

**AC-01-008** DADO no existe calibración, CUANDO se detecta gancho, ENTONCES puede mostrarse detección en píxeles pero no posición física válida.

**AC-01-009** DADA raw_position válida y alpha válido, CUANDO se aplica EMA, ENTONCES se conserva raw y se genera filtered.

**AC-01-010** DADO cambio de cámara/resolución, CUANDO existe calibración, ENTONCES pasa a INVALID.

**AC-01-011** DADA reconexión equivalente, CUANDO no cambió cámara/resolución/geometría conocida, ENTONCES la reconexión sola no invalida.

**AC-01-012** DADA Calibration de SPEC-01, CUANDO finaliza la app, ENTONCES no se garantiza recuperación posterior porque la persistencia pertenece a SPEC-02.

**AC-01-013** DADA observación del pipeline, CUANDO se entrega a Application, ENTONCES es VisionObservation interna y no WebSocket.

**AC-01-014** DADA detección clásica, CUANDO se muestra confidence, ENTONCES se identifica como score y no probabilidad.

**AC-01-015** DADO objeto perdido, CUANDO no hay observación actual válida, ENTONCES coordenadas anteriores no se muestran como actuales.

**AC-01-016** DADA implementación SPEC-01, CUANDO se inspecciona, ENTONCES no requiere ONNX, SQLite, WebSocket ni librerías nuevas.

**AC-01-017** DADA validación física, CUANDO se evalúa precisión, ENTONCES se reportan mediciones reales y no tolerancias inventadas.

---

## 23. Definition of Done

```text
✓ SPEC-00 sigue funcional
✓ Vision Worker implementado
✓ DetectorPort implementado
✓ OpenCvHookDetector implementado
✓ detección directa de gancho celeste
✓ configuración HSV validada
✓ contornos/scoring implementados
✓ CSRT integrado
✓ redetección implementada
✓ Calibration implementada
✓ 4-point homography implementada
✓ CalibrationRepositoryPort implementado
✓ InMemoryCalibrationRepository implementado
✓ invalidación cámara/resolución implementada
✓ PositionEstimatorPort implementado
✓ HomographyPositionEstimator implementado
✓ X/Y disponibles con calibración
✓ Z null
✓ raw_position
✓ EMA
✓ filtered_position
✓ angle null
✓ VisionObservation
✓ CALIBRACIÓN funcional
✓ DETECCIÓN funcional
✓ LIVE overlays
✓ UI no bloqueada
✓ tests automatizables pasan
✓ errores principales cubiertos
✓ documentación actualizada
✓ no SQLite
✓ no WebSocket
✓ no ONNX productivo
✓ no control ESP32
✓ no operaciones Git por agentes
```

### 23.1. VALIDADO EN SOFTWARE

Requiere tests unitarios, integración, calibración sintética, homografía conocida, EMA, estados y arquitectura.

### 23.2. VALIDADO EN HARDWARE

Requiere cámara real, gancho real, iluminación objetivo, tracking real, cuatro puntos físicos, puntos de validación adicionales y medición de error X/Y.

No declarar precisión física a partir de fixtures.

---

## 24. Dependencias con otras SPECS

### DEPENDE DE

**SPEC-00 — VALIDATED**

Consume:

```text
CameraPort
OpenCvCamera
Frame
LatestFrameStore
CameraController
Camera Worker
MainWindow
LIVE
logging base
```

SPEC-01 no rediseñará silenciosamente el lifecycle de cámara.

La limitación conocida de retirada USB con DSHOW registrada en SPEC-00 permanece aceptada.

### DESBLOQUEA

**SPEC-02 — Protocolo, WebSocket, persistencia, analítica, reportes y diagnósticos**

Proporciona:

```text
Detection
TrackingResult
Calibration
PositionEstimate
VisionObservation
estados de pipeline
métricas inmediatas
eventos
```

SPEC-02 podrá implementar:

```text
VisionObservation
  ↓
VisionReport
  ↓
JSON
  ↓
WebSocket
```

Y un adapter persistente para CalibrationRepositoryPort.

### NO DEBE MODIFICAR

SPEC-01 no define de forma definitiva:

- protocolo WebSocket;
- schema JSON;
- SQLite;
- retención;
- reportes históricos;
- analítica histórica;
- ONNX/GPU;
- release Windows.

---

## 25. Decisiones abiertas

### OPEN-01-001 — Unidad física estándar

**Pregunta:** ¿Qué unidad será el estándar global para X/Y en el contrato final?

**Motivo:** el usuario definió ejes, pero no fijó explícitamente la unidad estándar.

**Impacto:** VisionReport, persistencia, Mobile.

**Resolver en:** antes de aprobar contrato de SPEC-02.

### OPEN-01-002 — Parámetros físicos del detector

**Pregunta:** rangos HSV, áreas y morphology adecuados para el gancho real.

**Motivo:** dependen de cámara/iluminación/fondo.

**Impacto:** robustez.

**Resolver en:** pruebas físicas de SPEC-01.

### OPEN-01-003 — Umbral de confidence

**Pregunta:** score mínimo operativo.

**Motivo:** debe correlacionarse con hardware real.

**Resolver en:** pruebas físicas.

### OPEN-01-004 — Alpha operativo EMA

**Pregunta:** valor que equilibra jitter y retraso.

**Resolver en:** pruebas físicas.

### OPEN-01-005 — Precisión requerida para automatización futura

**Pregunta:** error máximo aceptable X/Y.

**Resolver en:** después del benchmark físico y antes de automatización que consuma posición.

---

## 26. Riesgos

### RISK-01-001 — Variación de iluminación
Probabilidad: Alta. Impacto: Alto. Mitigación: parámetros configurables, pruebas reales, morphology y eventual SPEC-03 si OpenCV no es suficiente.

### RISK-01-002 — Objetos celestes de fondo
Probabilidad: Media. Impacto: Alto. Mitigación: geometría, área, score, tracking y validación.

### RISK-01-003 — Brillos/reflejos
Probabilidad: Media. Impacto: Medio/Alto. Mitigación: tuning HSV y pruebas físicas.

### RISK-01-004 — Homografía insuficiente fuera del plano
Probabilidad: dependiente de mecánica. Impacto: Alto. Mitigación: validar puntos adicionales y documentar límites.

### RISK-01-005 — Z no observable
Estado: limitación de diseño. Impacto: Alto para 3D. Mitigación: Z=null y metodología futura si es necesaria.

### RISK-01-006 — Deriva CSRT
Probabilidad: Media. Impacto: Medio/Alto. Mitigación: redetección y tests.

### RISK-01-007 — EMA introduce retraso
Probabilidad: Alta si se ajusta mal. Impacto: Medio. Mitigación: raw preservado, alpha configurable y benchmark.

### RISK-01-008 — Movimiento físico de cámara no detectado automáticamente
Probabilidad: Media. Impacto: Alto. Mitigación: cámara fija, procedimiento operativo e invalidación manual.

### RISK-01-009 — Error interno de homografía interpretado como precisión real
Probabilidad: Alta. Impacto: Alto. Mitigación: advertencia y validación con puntos independientes.

### RISK-01-010 — Rendimiento CSRT + detector
Probabilidad: Media. Impacto: Medio. Mitigación: latest-frame y benchmark antes de optimizar.

### RISK-01-011 — Convención X/Y/Z distinta de documentos antiguos
Probabilidad: Alta si un consumidor usa contexto antiguo. Impacto: Alto. Mitigación: DEC-01-001 y obligatoriedad para SPEC-02/03.

---

## 27. Trazabilidad

| Requisito | Caso de uso | Test | Criterio |
|---|---|---|---|
| RF-01-001 a 006 | UC-01-01/02 | TC-01-001 a 003 | AC-01-001 |
| RF-01-007 a 011 | UC-01-04 | TC-01-004 a 007 | AC-01-002 |
| RF-01-012 a 028 | UC-01-03/04 | TC-01-004 a 009, 031 | AC-01-002, 014 |
| RF-01-029 a 034 | UC-01-05/06/07 | TC-01-010 a 012, 032 | AC-01-003/004 |
| RF-01-035 a 053 | UC-01-08/09 | TC-01-013 a 015, 019 a 022, 033 | AC-01-005, 010 a 012 |
| RF-01-054 a 064 | UC-01-10/11 | TC-01-016 a 018, 034 | AC-01-006 a 008 |
| RF-01-065 a 071 | UC-01-12 | TC-01-023 a 026 | AC-01-009 |
| RF-01-072/073 | UC-01-10 | TC-01-017 | AC-01-007 |
| RF-01-074 a 077 | UC-01-13 | TC-01-029/030 | AC-01-013/016 |
| RF-01-078 a 084 | UC-01-03/08/13 | TC-01-009/022/031 | AC-01-008/014/015 |
| RNF-01-001 a 006 | Todos | TC-01-029/030 | AC-01-013/016 |
| RNF-01-007 a 012 | UC-01-01/13 | TC-01-027/035 | AC-01-001 |
| RNF-01-013 a 015 | UC-01-14 | TC-01-033/034 | AC-01-017 |
| RNF-01-016 a 019 | UC-01-04 a 12 | TC-01-005/011/015/018 | AC-01-004/008/015 |
| RNF-01-020 a 023 | Todos | TC-01-004 a 030 | AC-01-016 |
| RNF-01-024 a 026 | Todos | revisión estática | AC-01-016 |
| RNF-01-027/028 | UC-01-13 | TC-01-029 | AC-01-015 |

---

## 28. Registro de implementación y verificación de software

### 28.1. Implementación entregada

Se implementaron los modelos de geometría, calibración, detección, tracking, posición y VisionObservation; los Ports; OpenCvHookDetector; CsrtTracker; OpenCvHomographySolver; HomographyPositionEstimator; InMemoryCalibrationRepository; EmaPositionFilter; CalibrationService y VisionPipelineController.

Vision Worker y cálculo de homografía se ejecutan fuera del hilo UI. LatestFrameStore incorpora un cursor de revisión independiente, sin alterar las operaciones de consumo existentes de SPEC-00. Una nueva sesión de visión no confunde secuencias de cámara reiniciadas. Los resultados tienen un único slot vigente y notificaciones coalescidas; el frame procesado se presenta junto con su observación.

CALIBRACIÓN y DETECCIÓN son pantallas funcionales. LIVE incorpora overlays, calidad y posición raw/filtered. Cambios de parámetros, calibración, cámara o resolución descartan resultados anteriores y reinician el estado correspondiente. Una resolución incompatible se detecta también dentro del pipeline antes de aplicar la homografía, aunque la notificación de UI aún no haya sido procesada.

CALIBRACIÓN permite registrar puntos de validación independientes y calcular agregados de MAE X/Y, error 2D medio y máximo para raw/filtered. Los agregados son efímeros, de memoria constante, y no implican persistencia ni una precisión física ya acreditada.

Los parámetros operativos permanecen sin defaults inventados: el usuario introduce HSV, área mínima, calidad mínima y alpha. La unidad se declara por calibración. La imagen completa mantiene coordenadas fuente; morfología opcional aplica apertura y cierre con kernel positivo impar que no excede las dimensiones del frame.

### 28.2. Verificación ejecutada

**Fecha de registro:** 6 de octubre de 2026.

```text
.venv\Scripts\python.exe -m pytest -q
104 passed, 1 skipped
```

La suite incluye regresiones de SPEC-00 y los comportamientos automatizables de TC-01-001 a TC-01-030: fixtures HSV/contornos, candidatos ambiguos, score, CSRT real en imágenes sintéticas, pérdida/deriva/reacquisición, homografía conocida, degeneración, finitud, Z=null, angle=null, EMA, invalidación, observación interna y arquitectura.

También verifica separación de consumidores UI/visión, reinicio de secuencia, productor rápido/consumidor lento, correspondencia entre frame y overlays, configuración explícita con errores en español, selección de puntos en imagen escalada y shutdown con visión/cálculo bloqueados, descartando resultados tardíos.

La prueba omitida corresponde al test opcional de cámara física de SPEC-00, que requiere índice explícito. Los tests de SPEC-01 utilizan datos sintéticos y fakes: el tracker OpenCV real fue probado en software, no con el gancho físico.

### 28.3. Estado y validación física pendiente

**VALIDADO EN SOFTWARE** para los escenarios automatizados registrados. No se declara detección, tracking ni precisión físicamente validados.

Permanecen pendientes TC-01-031 a TC-01-036: ajuste HSV/áreas/morfología/calidad/alpha con gancho real, tracking y redetección físicos, cuatro correspondencias físicas, referencias adicionales, medición de precisión X/Y, benchmark de pipeline e invalidación tras mover la cámara.

El estado documental permanece APPROVED hasta completar y revisar las condiciones de implementación/validación que dependen del hardware. OPEN-01-001 a OPEN-01-005 conservan los momentos de resolución previstos: esta entrega no fija unidad global, parámetros del gancho real ni objetivos numéricos de automatización.

La limitación USB con DSHOW aceptada en SPEC-00 se hereda, según la sección 24; no se afirma una mejora de detección física del dispositivo. Las instrucciones operativas y de validación se encuentran en README.md.

---

# Anexo A — Decisiones cerradas

```text
DEC-01-001
X = horizontal, Y = vertical, Z = profundidad.

DEC-01-002
Detección directa del gancho físico; sin marcador.

DEC-01-003
El gancho celeste se detecta inicialmente con color/contornos OpenCV.

DEC-01-004
Calibración V1 = homografía con cuatro correspondencias manuales.

DEC-01-005
X/Y se estiman mediante homografía; Z = null.

DEC-01-006
Se procesa inicialmente toda la imagen; no ROI obligatoria.

DEC-01-007
Calibración se invalida por cambio de cámara, resolución o geometría física reportada; reconexión equivalente no la invalida por sí sola.

DEC-01-008
Calibración en memoria en SPEC-01; persistencia en SPEC-02.

DEC-01-009
Detector se activa manualmente.

DEC-01-010
Tracking V1 = CSRT.

DEC-01-011
Pérdida de tracking vuelve al detector para reacquirir.

DEC-01-012
PositionEstimate conserva raw_position y filtered_position.

DEC-01-013
Suavizado = EMA; alpha TBD mediante pruebas físicas.

DEC-01-014
Confidence = quality score 0..1, no probabilidad estadística.

DEC-01-015
Precisión X/Y se mide experimentalmente; no se inventa tolerancia.

DEC-01-016
angle = null en SPEC-01.

DEC-01-017
SPEC-01 termina en VisionObservation interna; VisionReport/protocolo corresponde a SPEC-02.
```

---

# Anexo B — Estructura esperada

```text
src/blanquita_vision/
├── domain/
│   ├── models/
│   │   ├── calibration.py
│   │   ├── detection.py
│   │   ├── tracking.py
│   │   ├── position.py
│   │   └── vision_observation.py
│   └── ports/
│       ├── detector_port.py
│       ├── tracker_port.py
│       ├── position_estimator_port.py
│       └── calibration_repository_port.py
├── application/
│   ├── vision_pipeline_controller.py
│   ├── calibration_service.py
│   └── position_filter.py
├── adapters/
│   ├── detection/
│   │   ├── opencv_hook_detector.py
│   │   └── csrt_tracker.py
│   ├── calibration/
│   │   └── in_memory_calibration_repository.py
│   └── position/
│       └── homography_position_estimator.py
└── presentation/
    ├── screens/
    │   ├── live_screen.py
    │   ├── calibration_screen.py
    │   └── detection_screen.py
    └── workers/
        └── vision_worker.py
```

Orientativa; evitar clases redundantes y sobreingeniería.

---

# Anexo C — Fórmulas

## C.1. Homografía

```text
[x']
[y'] = H [u, v, 1]^T
[w']

X = x' / w'
Y = y' / w'
Z = null
```

si `w'` y el resultado son numéricamente válidos.

## C.2. EMA

```text
filtered_t = alpha * raw_t + (1-alpha) * filtered_(t-1)
```

con:

```text
0 < alpha <= 1
alpha operativo = TBD
```

## C.3. Error físico

```text
error_x = |x_est - x_real|
error_y = |y_est - y_real|
error_2d = sqrt((x_est-x_real)^2 + (y_est-y_real)^2)
```

---

# Revisión de completitud

```text
✓ SPEC-00 revisada y VALIDATED
✓ objetivo visual definido
✓ detector clásico definido
✓ sin marcador
✓ sin ONNX adelantado
✓ preprocessing definido
✓ DetectorPort definido
✓ CSRT definido
✓ reacquisición definida
✓ calibración homográfica definida
✓ cuatro puntos manuales definidos
✓ no se inventa origen
✓ convención X/Y/Z actualizada explícitamente
✓ X/Y estimables
✓ Z null
✓ PositionEstimatorPort definido
✓ raw/filtered definidos
✓ EMA definida
✓ alpha no inventado
✓ confidence definido como score
✓ angle null
✓ VisionObservation interna
✓ WebSocket fuera de alcance
✓ SQLite fuera de alcance
✓ concurrencia definida
✓ errores definidos
✓ observabilidad definida
✓ UI/UX definida
✓ tests software definidos
✓ tests hardware definidos
✓ benchmark precisión definido
✓ no se inventa precisión
✓ criterios de aceptación definidos
✓ Definition of Done definida
✓ riesgos definidos
✓ trazabilidad definida
✓ no comunicación directa con ESP32
✓ no responsabilidades de Mobile trasladadas a laptop
```

---

# Estado final

```text
SPEC-01
Pipeline de visión, calibración, detección y estimación de posición

ESTADO: APPROVED

DEPENDENCIA: SPEC-00 VALIDATED

SIGUIENTE PASO:
Implementación funcional entregada y validada en software.
Realizar tuning y validación con el gancho/cámara reales,
correspondencias físicas y puntos independientes (sección 28).

DESBLOQUEA TRAS IMPLEMENTACIÓN/VALIDACIÓN:
SPEC-02 — Protocolo, WebSocket, persistencia, analítica,
reportes y diagnósticos.

NO IMPLEMENTAR SPEC-02 AUTOMÁTICAMENTE.
```

## Políticas aprobadas para implementación

El usuario aprobó expresamente SPEC-01 y las políticas siguientes antes de implementar:

1. Score de calidad = solidez del contorno × ocupación de la máscara celeste dentro de su bounding box. Ambos factores pertenecen a [0,1]. Restricciones de área configurables; empate entre candidatos principales produce ausencia de selección inequívoca.
2. Detector y CSRT se ejecutan en cada frame procesado. El seguimiento se valida con una detección actual y una intersección positiva entre cajas. Una pérdida o incompatibilidad reinicia tracking mediante redetección. La calidad mostrada procede de la detección actual, no de una probabilidad atribuida a CSRT.
3. El punto usado para posición física es el centro de la caja validada, tanto al inicializar como al seguir. El centroide del contorno se conserva como geometría de detección.
4. Cambios de parámetros o calibración descartan resultados pendientes y reinician tracker/EMA. Desconectar la cámara detiene la visión; el siguiente inicio es manual.
5. Con visión activa se presenta el frame procesado con sus overlays asociados. Sin visión activa se presenta la captura vigente.
6. HSV, área mínima, calidad mínima y alpha se introducen explícitamente antes del primer inicio. No se fijan parámetros operativos del hardware. La unidad se declara por calibración; el estándar global queda pendiente para SPEC-02.

La detección conserva X horizontal, Y vertical y Z=null; esta autorización no cambia automáticamente los documentos base anteriores.
