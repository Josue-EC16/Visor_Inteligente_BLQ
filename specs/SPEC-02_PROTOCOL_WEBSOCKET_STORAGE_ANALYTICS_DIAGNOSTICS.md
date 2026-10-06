# SPEC-02 — Protocolo, WebSocket, persistencia, analítica, reportes y diagnósticos

## 1. Identificación

| Campo | Valor |
|---|---|
| SPEC ID | SPEC-02 |
| Nombre | Protocolo, WebSocket, persistencia, analítica, reportes y diagnósticos |
| Archivo oficial | `SPEC-02_PROTOCOL_WEBSOCKET_STORAGE_ANALYTICS_DIAGNOSTICS.md` |
| Versión | 1.0.0 |
| Estado | IMPLEMENTED |
| Proyecto | BLANQUITA Vision |
| Plataforma | Windows 10 / Windows 11 x64 |
| Fecha | 2026-10-06 |
| Dependencias | SPEC-00 + SPEC-01 |
| Estado requerido SPEC-00 | VALIDATED |
| Estado aceptado SPEC-01 | APPROVED + implementación funcional validada en software |
| Spec relacionada siguiente | SPEC-03 |

### 1.1. Fuentes normativas

1. `AGENTS.md`
2. `VISION_INTELIGENTE_BLQ.md`
3. `ARQUITECTURA_CONEXION.md`
4. `APP_MOVIL_BLANQ_V2.md`
5. `SPEC-00_FOUNDATION_ARCHITECTURE_UI_CAPTURE.md`
6. `SPEC-01_VISION_PIPELINE_CALIBRATION_DETECTION_POSITION.md`
7. Decisiones explícitas aprobadas por el usuario para SPEC-02.

### 1.2. Autorización de avance sobre SPEC-01

El usuario autoriza desarrollar SPEC-02 utilizando como contratos estables de software los modelos y puertos aprobados/implementados en SPEC-01 aunque su validación física con el gancho/cámara reales continúe pendiente.

Esto NO cambia automáticamente SPEC-01 a `VALIDATED`.

SPEC-02 deberá consumir sin rediseñar silenciosamente:

```text
Detection
TrackingResult
Calibration
CalibrationStatus
PositionEstimate
VisionObservation
VisionPipelineState
```

### 1.3. Convención oficial de ejes

La convención heredada y obligatoria es:

```text
X = horizontal: izquierda ↔ derecha
Y = vertical: abajo ↔ arriba
Z = profundidad
```

Durante SPEC-02:

```text
X = disponible con calibración válida
Y = disponible con calibración válida
Z = null
```

### 1.4. Unidad física oficial

A partir de SPEC-02 la unidad estándar para coordenadas físicas será:

```text
mm
```

Aplica a protocolo, SQLite, reportes, exportaciones, analítica, calibración persistida y contrato con BLANQUITA Mobile.

### 1.5. Política temporal transversal

Todos los timestamps persistidos o intercambiados deberán estar normalizados a:

```text
UTC
ISO-8601
timezone-aware
sufijo Z
```

Ejemplo:

```text
2026-10-06T15:30:00.123Z
```

Regla general:

```text
persistencia/intercambio = UTC
presentación UI = zona horaria local del sistema
```

No se almacenarán timestamps ingenuos sin zona para datos operativos de SPEC-02.

---

## 2. Contexto

SPEC-00 proporciona captura, shell y lifecycle de cámara.

SPEC-01 proporciona percepción estructurada:

```text
Frame
  ↓
Detection
  ↓
TrackingResult
  ↓
PositionEstimate
  ↓
VisionObservation
```

SPEC-02 convierte esa percepción local en un subsistema operativo completo:

```text
VisionObservation
   │
   ├── Protocol Mapper
   │      ↓
   │   VisionReport
   │      ↓
   │   WebSocket → Mobile
   │
   ├── Storage Worker
   │      ↓
   │   SQLite + filesystem
   │
   ├── Analytics
   ├── Reports
   └── Diagnostics
```

BLANQUITA Vision continúa siendo únicamente una fuente de percepción.

BLANQUITA Mobile continúa siendo la única autoridad de decisión de alto nivel.

---

## 3. Objetivo

Implementar la capa de comunicación, persistencia y observabilidad de BLANQUITA Vision para:

1. transformar `VisionObservation` en `VisionReport` versionado;
2. validar mensajes con Pydantic;
3. exponer un servidor WebSocket local;
4. aceptar un único cliente Mobile activo;
5. emitir reportes sin acumular datos obsoletos;
6. recibir `vision.start`, `vision.stop` y `vision.ping`;
7. mantener heartbeat de aplicación;
8. persistir datos estructurados en SQLite;
9. persistir capturas manuales en filesystem;
10. persistir y recuperar calibraciones compatibles;
11. registrar sesiones, reportes, detecciones, eventos, errores y métricas;
12. habilitar ANALÍTICA;
13. habilitar REPORTES;
14. habilitar DIAGNÓSTICOS;
15. conservar UI responsiva mediante Network Worker y Storage Worker;
16. funcionar sin Internet;
17. mantener separación estricta respecto del control físico.

---

## 4. Alcance

### 4.1. IN SCOPE

#### Protocolo

- JSON versionado.
- `protocol = "blanquita-vision"`.
- `version = 1`.
- UUID `messageId`.
- timestamps UTC.
- Pydantic 2.13.5.
- `vision.hello`.
- `vision.ready`.
- `vision.status`.
- `vision.report`.
- `vision.error`.
- `vision.heartbeat`.
- `camera.status`.
- `calibration.status`.
- `vision.start`.
- `vision.stop`.
- `vision.ping`.
- start/stop idempotentes.
- validación estricta de mensajes.

#### WebSocket

- `websockets==17.1`.
- laptop = servidor.
- Mobile = cliente.
- bind IPv4 `0.0.0.0`.
- puerto `8765`.
- path `/vision`.
- un cliente activo.
- server startup automático.
- heartbeat cada 2 segundos.
- stale contractual a 6 segundos.
- sin TLS en V1.
- sin autenticación en V1.
- LAN privada.
- latest-only para reportes salientes pendientes.

#### VisionReport

- derivado de `VisionObservation`.
- `filtered_position` como posición oficial.
- unidad mm.
- X/Y nullable.
- Z nullable y actualmente null.
- angle nullable y actualmente null.
- confidence como quality score 0..1.
- calibrationStatus.
- trackingState.
- frameSequence.
- observation timestamp.

#### Persistencia

- SQLite con `sqlite3`.
- WAL.
- versionado de schema.
- `VisionRepositoryPort`.
- `SQLiteVisionRepository`.
- adapter persistente de `CalibrationRepositoryPort`.
- Storage Worker.
- sesiones.
- detecciones.
- reportes emitidos.
- calibraciones.
- puntos de calibración.
- eventos.
- errores.
- muestras métricas.
- configuración.
- referencias a capturas.
- retención indefinida V1.

#### Capturas

- solo manuales.
- JPEG y PNG seleccionables.
- archivo físico en `data/captures/` o path configurado.
- metadata/ruta en SQLite.
- no BLOB grande.

#### Analítica

- tiempo real e histórico.
- PyQtGraph.
- FPS.
- latencias.
- confidence.
- X/Y raw y filtered.
- detecciones.
- tracking lost/reacquisitions.
- errores.
- muestras históricas 1/s.
- Polars opcional y fuera del pipeline crítico.

#### Reportes

- sesiones.
- detecciones.
- VisionReports.
- capturas.
- calibraciones.
- eventos.
- errores.
- búsqueda.
- filtros.
- detalle.
- export JSON.
- export CSV.

#### Diagnósticos

- CAMERA.
- VISION.
- NETWORK.
- DATABASE.
- FILESYSTEM.
- SYSTEM.
- sin `psutil` ni nueva dependencia.

### 4.2. OUT OF SCOPE

- ONNX productivo.
- entrenamiento ML.
- GPU/CUDA.
- `onnxruntime-gpu`.
- selección/evaluación final de modelos.
- release `.exe`.
- instalador.
- TLS/WSS.
- autenticación/token.
- Internet/cloud.
- MQTT.
- múltiples clientes simultáneos.
- transmisión de video al móvil.
- grabación continua.
- captura automática por cada detección.
- eliminación automática de históricos.
- backups automáticos.
- control directo de ESP32.
- comandos de motor.
- modificación de HSV/CSRT/homografía/EMA aprobados en SPEC-01.

---

## 5. Actores

### 5.1. Usuario operador

Puede consultar y operar funciones locales de visión, analítica, reportes, capturas y diagnósticos.

### 5.2. BLANQUITA Mobile

Cliente WebSocket remoto.

Puede:

- conectarse;
- recibir estados/reportes/errores/heartbeat;
- iniciar visión;
- detener visión;
- enviar ping.

No puede:

- controlar motores por este canal;
- acceder directamente a SQLite;
- escribir paths arbitrarios;
- controlar ESP32 a través de la laptop.

### 5.3. Vision Pipeline

Productor de `VisionObservation`.

### 5.4. Network Worker

Propietario del servidor WebSocket.

### 5.5. Storage Worker

Responsable de persistencia bloqueante.

### 5.6. SQLite

Almacén local estructurado.

### 5.7. Filesystem

Almacén de capturas físicas.

---

## 6. Casos de uso

### UC-02-01 — Iniciar servidor WebSocket

**Actor:** Sistema.

**Precondiciones:** aplicación iniciada, configuración válida, puerto disponible.

**Trigger:** bootstrap de BLANQUITA Vision.

**Flujo:**

1. Crear Network Worker.
2. Inicializar servidor.
3. Bind en `0.0.0.0:8765`.
4. Aceptar exclusivamente `/vision`.
5. Pasar a LISTENING.
6. Exponer estado a UI/Diagnósticos.

**Errores:** puerto ocupado, fallo de socket, configuración inválida.

### UC-02-02 — Conectar Mobile

**Precondición:** LISTENING y sin cliente activo.

1. validar path;
2. aceptar conexión;
3. registrar cliente activo;
4. enviar `vision.hello`;
5. enviar `vision.ready`;
6. emitir estados iniciales;
7. iniciar heartbeat;
8. actualizar diagnóstico.

### UC-02-03 — Rechazar segundo cliente

Si existe cliente activo, un segundo cliente se rechaza sin desplazar al primero.

### UC-02-04 — Recibir vision.start

1. parsear JSON;
2. validar Pydantic;
3. ejecutar el mismo caso de uso de inicio que utiliza UI local;
4. si ya RUNNING, responder/actuar idempotentemente;
5. emitir estado;
6. registrar evento.

Conectarse no inicia visión automáticamente.

### UC-02-05 — Recibir vision.stop

1. validar;
2. ejecutar StopVision;
3. si ya STOPPED, mantener idempotencia;
4. emitir estado;
5. registrar evento.

No implica desconectar cámara.

### UC-02-06 — Recibir vision.ping

1. validar mensaje;
2. responder inmediatamente con `vision.heartbeat`;
3. incluir `replyToMessageId`;
4. actualizar RX/TX.

No se introduce `vision.pong` en V1.

### UC-02-07 — Heartbeat periódico

Con cliente activo:

```text
cada 2 segundos → vision.heartbeat
```

Contrato Mobile:

```text
6 segundos sin heartbeat válido → Vision Server stale
```

### UC-02-08 — Emitir VisionReport

1. recibir VisionObservation;
2. seleccionar filtered_position;
3. normalizar unidad mm;
4. aplicar reglas null;
5. crear Pydantic model;
6. serializar;
7. mantener como último reporte pendiente;
8. reemplazar pending anterior no enviado;
9. enviar;
10. persistir el reporte realmente emitido.

### UC-02-09 — Objeto no detectado

```text
detected = false
x = null
y = null
z = null
angle = null
```

Nunca reutilizar last-known-position como actual.

### UC-02-10 — Detectado sin calibración

```text
detected = true
object = gancho
x = null
y = null
z = null
calibrationStatus != VALID
```

### UC-02-11 — Detectado con calibración

```text
detected = true
x = filtered X mm
y = filtered Y mm
z = null
angle = null
```

### UC-02-12 — Mensaje remoto inválido

1. parsear;
2. validar envelope/payload;
3. no ejecutar acción;
4. enviar `vision.error` cuando corresponda;
5. registrar error;
6. mantener/cerrar conexión según severidad.

### UC-02-13 — Crear sesión de visión

Una `vision_session` comienza cuando el pipeline transiciona realmente a RUNNING.

Guardar:

- start UTC;
- origen `local_ui` o `mobile`;
- camera_id;
- resolución.

### UC-02-14 — Cerrar sesión de visión

Cierra por:

- stop local;
- stop Mobile;
- shutdown;
- error fatal;
- pérdida de condición necesaria que finalice pipeline.

Guardar end UTC y reason.

### UC-02-15 — Persistir calibración

Al aplicar Calibration VALID:

1. validar mm;
2. guardar perfil;
3. guardar cuatro puntos;
4. guardar homografía;
5. registrar evento.

### UC-02-16 — Recuperar calibración compatible

Cuando camera_id + width + height sean conocidos:

1. buscar Calibration VALID más reciente compatible;
2. cargarla mediante CalibrationRepositoryPort;
3. validar estructura;
4. exponer estado.

No se puede inferir automáticamente si físicamente se movió la cámara.

### UC-02-17 — Captura manual

1. solicitar snapshot;
2. seleccionar JPG/PNG configurado;
3. generar filename único;
4. guardar filesystem;
5. verificar escritura;
6. insertar metadata SQLite;
7. informar éxito.

Un fallo físico de archivo no se registra como captura exitosa.

### UC-02-18 — Agregar muestra métrica

Durante una sesión activa:

```text
1 muestra agregada / segundo
```

No una fila por frame.

### UC-02-19 — Consultar analítica

1. seleccionar vista/período;
2. consultar datos;
3. procesar fuera de UI si corresponde;
4. graficar;
5. conservar pipeline independiente.

### UC-02-20 — Consultar reportes

Listar/filtrar/paginar sesiones, detecciones, reportes, capturas, calibraciones, eventos y errores.

### UC-02-21 — Exportar JSON

Ruta elegida localmente mediante diálogo. Exportar timestamps UTC, mm y null sin falsificación.

### UC-02-22 — Exportar CSV

Misma política que JSON con columnas estables.

### UC-02-23 — Consultar diagnósticos

Mostrar health snapshot de cámara, visión, red, DB, filesystem y sistema. Un valor no obtenible de forma fiable debe mostrarse como `No disponible`.

---

## 7. Requisitos funcionales

### Protocolo

**RF-02-001** El sistema deberá utilizar JSON versionado.

**RF-02-002** Todo mensaje deberá incluir `protocol`.

**RF-02-003** `protocol` será exactamente `blanquita-vision`.

**RF-02-004** Todo mensaje deberá incluir `version`.

**RF-02-005** La versión inicial será `1`.

**RF-02-006** Todo mensaje deberá incluir `type`.

**RF-02-007** Todo mensaje deberá incluir `messageId`.

**RF-02-008** `messageId` deberá ser UUID válido.

**RF-02-009** Todo mensaje deberá incluir `timestamp`.

**RF-02-010** Todo timestamp de protocolo deberá estar en UTC ISO-8601 aware con `Z`.

**RF-02-011** Todo mensaje deberá contener `payload`.

**RF-02-012** Los mensajes deberán validarse mediante Pydantic.

**RF-02-013** Un mensaje inválido no deberá ejecutar acciones.

**RF-02-014** Una versión incompatible deberá producir error explícito.

### Laptop → Mobile

**RF-02-015** Soportar `vision.hello`.

**RF-02-016** Soportar `vision.ready`.

**RF-02-017** Soportar `vision.status`.

**RF-02-018** Soportar `vision.report`.

**RF-02-019** Soportar `vision.error`.

**RF-02-020** Soportar `vision.heartbeat`.

**RF-02-021** Soportar `camera.status`.

**RF-02-022** Soportar `calibration.status`.

### Mobile → Laptop

**RF-02-023** Aceptar `vision.start`.

**RF-02-024** Aceptar `vision.stop`.

**RF-02-025** Aceptar `vision.ping`.

**RF-02-026** Start será idempotente.

**RF-02-027** Stop será idempotente.

**RF-02-028** Ping responderá con heartbeat correlacionable.

### WebSocket

**RF-02-029** BLANQUITA Vision será servidor WebSocket.

**RF-02-030** Usará `websockets==17.1`.

**RF-02-031** Bind inicial IPv4 `0.0.0.0`.

**RF-02-032** Puerto `8765`.

**RF-02-033** Path `/vision`.

**RF-02-034** Paths distintos deberán rechazarse.

**RF-02-035** El servidor iniciará automáticamente con la app.

**RF-02-036** Ausencia de Mobile no impedirá visión local.

**RF-02-037** Máximo un cliente activo.

**RF-02-038** Segundo cliente será rechazado sin desplazar al primero.

**RF-02-039** No requerir Internet.

**RF-02-040** V1 utilizará `ws://`.

**RF-02-041** V1 no implementará autenticación.

**RF-02-042** Se documentará LAN privada/no exposición directa a Internet.

### Heartbeat

**RF-02-043** Enviar heartbeat cada 2 s con cliente activo.

**RF-02-044** Documentar stale Mobile = 6 s sin heartbeat válido.

**RF-02-045** Heartbeat deberá contener server time UTC.

**RF-02-046** Respuesta a ping podrá contener `replyToMessageId`.

### VisionReport

**RF-02-047** Derivar VisionReport de VisionObservation.

**RF-02-048** Usar filtered_position como posición oficial.

**RF-02-049** Unidad oficial `mm`.

**RF-02-050** Incluir `detected`.

**RF-02-051** Incluir `object`.

**RF-02-052** Incluir `position`.

**RF-02-053** Position incluirá `x`, `y`, `z`, `angle`, `unit`.

**RF-02-054** Incluir `confidence`.

**RF-02-055** Incluir `calibrationStatus`.

**RF-02-056** Incluir `trackingState`.

**RF-02-057** Incluir `frameSequence`.

**RF-02-058** Incluir `observationTimestamp` UTC.

**RF-02-059** Si detected=false, X/Y/Z serán null.

**RF-02-060** Si detected=true sin calibración válida, X/Y/Z físicos serán null.

**RF-02-061** Con calibración válida X/Y podrán tener valores.

**RF-02-062** Z permanecerá null.

**RF-02-063** Angle permanecerá null mientras SPEC-01 no lo produzca.

**RF-02-064** No reutilizar coordenadas anteriores como actuales.

**RF-02-065** Confidence conservará semántica quality score 0..1.

### Latest-only

**RF-02-066** Intentar un report por nueva VisionObservation con cliente conectado.

**RF-02-067** Si red es más lenta, conservar solo report pendiente más reciente.

**RF-02-068** La cola de reports pendientes no crecerá ilimitadamente.

**RF-02-069** Solo reportes realmente emitidos se persistirán como emitidos.

### Persistencia

**RF-02-070** Utilizar SQLite mediante `sqlite3`.

**RF-02-071** DB local.

**RF-02-072** Activar WAL cuando sea compatible.

**RF-02-073** Versionar schema.

**RF-02-074** Acceso mediante `VisionRepositoryPort`.

**RF-02-075** Implementación `SQLiteVisionRepository`.

**RF-02-076** Escrituras bloqueantes fuera del UI thread.

**RF-02-077** Usar Storage Worker.

**RF-02-078** Fallo Storage no bloqueará permanentemente UI/Network.

### Sesiones

**RF-02-079** Crear sesión cuando pipeline realmente llegue a RUNNING.

**RF-02-080** Guardar start UTC.

**RF-02-081** Guardar origen `local_ui` o `mobile`.

**RF-02-082** Guardar camera_id y resolución si existen.

**RF-02-083** Guardar end UTC.

**RF-02-084** Guardar reason de cierre.

### Detecciones/reportes

**RF-02-085** Guardar detecciones asociables a sesión.

**RF-02-086** Guardar reportes realmente emitidos.

**RF-02-087** Conservar messageId.

**RF-02-088** Conservar frameSequence.

**RF-02-089** Conservar raw X/Y cuando existan.

**RF-02-090** Conservar filtered X/Y cuando existan.

**RF-02-091** Z será nullable.

### Calibraciones

**RF-02-092** Proporcionar adapter persistente de CalibrationRepositoryPort.

**RF-02-093** Calibration VALID aplicada se persistirá automáticamente.

**RF-02-094** Conservar exactamente cuatro puntos V1.

**RF-02-095** Conservar matriz homography.

**RF-02-096** Conservar camera_id.

**RF-02-097** Conservar width/height.

**RF-02-098** Unidad persistida = mm.

**RF-02-099** Cargar calibración válida más reciente compatible con camera_id + resolución.

**RF-02-100** Auto-load no implicará que la cámara no fue movida.

**RF-02-101** Invalidación deberá persistirse.

### Capturas

**RF-02-102** Guardar imágenes en filesystem, no BLOB grande.

**RF-02-103** V1 guardará imágenes solo por solicitud manual.

**RF-02-104** Formato selectable JPG/PNG.

**RF-02-105** Extensión corresponderá al encoding real.

**RF-02-106** SQLite guardará ruta relativa/portable cuando sea posible.

**RF-02-107** Guardar timestamp UTC.

**RF-02-108** Guardar session_id si existe.

**RF-02-109** Guardar frame_sequence si existe.

**RF-02-110** Guardar metadata detección/posición asociada cuando corresponda.

**RF-02-111** Fallo de escritura no se registrará como éxito.

### Métricas

**RF-02-112** Persistir una muestra agregada por segundo durante sesión activa.

**RF-02-113** No insertar fila métrica por frame.

**RF-02-114** Métricas podrán incluir capture/pipeline FPS.

**RF-02-115** Incluir tiempos agregados preprocess/detection/tracking/position/filter/total cuando existan.

**RF-02-116** Incluir confidence agregada cuando corresponda.

**RF-02-117** Incluir conteos detección/tracking lost/reacquisition/errors.

### Eventos/errores

**RF-02-118** Persistir eventos relevantes.

**RF-02-119** Persistir errores relevantes.

**RF-02-120** Error contendrá componente/código/mensaje/recoverable.

**RF-02-121** No persistir secretos inexistentes/innecesarios.

### Configuración

**RF-02-122** Persistir ajustes de SPEC-02.

**RF-02-123** Validar configuración antes de aplicar.

**RF-02-124** Persistir formato de captura.

**RF-02-125** Mantener endpoint aprobado salvo cambio autorizado.

### Retención

**RF-02-126** No eliminar registros automáticamente por antigüedad.

**RF-02-127** No eliminar capturas automáticamente por antigüedad.

**RF-02-128** Limpieza automática fuera de alcance.

### Analítica

**RF-02-129** ANALÍTICA será funcional.

**RF-02-130** Mostrar métricas tiempo real.

**RF-02-131** Consultar histórico SQLite.

**RF-02-132** Mostrar FPS.

**RF-02-133** Mostrar latencias pipeline.

**RF-02-134** Mostrar confidence.

**RF-02-135** Mostrar X/Y raw y filtered.

**RF-02-136** Z se mostrará no disponible.

**RF-02-137** Mostrar detecciones y errores.

**RF-02-138** Histórico no bloqueará pipeline.

### Reportes

**RF-02-139** REPORTES será funcional.

**RF-02-140** Consultar sesiones.

**RF-02-141** Consultar detecciones.

**RF-02-142** Consultar VisionReports.

**RF-02-143** Consultar capturas.

**RF-02-144** Consultar calibraciones.

**RF-02-145** Consultar eventos.

**RF-02-146** Consultar errores.

**RF-02-147** Aplicar filtros.

**RF-02-148** Abrir captura existente.

**RF-02-149** Exportar JSON.

**RF-02-150** Exportar CSV.

**RF-02-151** Ruta export elegida localmente por usuario.

### Diagnósticos

**RF-02-152** DIAGNÓSTICOS será funcional.

**RF-02-153** Mostrar CAMERA.

**RF-02-154** Mostrar VISION.

**RF-02-155** Mostrar NETWORK.

**RF-02-156** Mostrar DATABASE.

**RF-02-157** Mostrar FILESYSTEM.

**RF-02-158** Mostrar SYSTEM obtenible con stack aprobado.

**RF-02-159** Mostrar endpoint WebSocket.

**RF-02-160** Mostrar cliente connected/disconnected.

**RF-02-161** Mostrar last RX/TX.

**RF-02-162** Mostrar heartbeat state.

**RF-02-163** Mostrar DB path/WAL/schema version.

**RF-02-164** Mostrar capture path/writability.

**RF-02-165** CPU/RAM/GPU detallados no deberán inventarse si no son obtenibles fiablemente.

---

## 8. Requisitos no funcionales

**RNF-02-001** Mantener Arquitectura Hexagonal + Ports & Adapters.

**RNF-02-002** Domain no dependerá directamente de `websockets`, `sqlite3` o PySide6 cuando exista Port.

**RNF-02-003** WebSocketVisionServer estará detrás de ReportPublisherPort/equivalente.

**RNF-02-004** SQLiteVisionRepository implementará VisionRepositoryPort.

**RNF-02-005** Persistencia de calibración mantendrá contrato de SPEC-01.

**RNF-02-006** WebSocket loop no bloqueará UI.

**RNF-02-007** SQLite/filesystem no bloquearán UI.

**RNF-02-008** Network Worker/Storage Worker tendrán lifecycle explícito.

**RNF-02-009** Shutdown cerrará workers ordenadamente.

**RNF-02-010** Latencia WebSocket objetivo = TBD mediante benchmark.

**RNF-02-011** Tiempo de consulta histórica objetivo = TBD.

**RNF-02-012** Medir rendimiento sin inventar umbrales.

**RNF-02-013** Latest-only evitará acumulación de reports.

**RNF-02-014** messageId único por mensaje generado.

**RNF-02-015** Persistencia temporal UTC.

**RNF-02-016** Export mantiene mm.

**RNF-02-017** Usar foreign keys cuando corresponda.

**RNF-02-018** Operaciones compuestas usarán transacciones.

**RNF-02-019** V1 no se expondrá directamente a Internet.

**RNF-02-020** Mensaje remoto inválido no ejecutará casos de uso.

**RNF-02-021** Canal visión no permitirá comandos físicos.

**RNF-02-022** Ausencia de autenticación se documentará como limitación LAN V1.

**RNF-02-023** Datos externos no controlarán paths arbitrarios.

**RNF-02-024** Caída de Mobile no cerrará aplicación/visión local automáticamente.

**RNF-02-025** Caída SQLite degradará storage sin fabricar éxito.

**RNF-02-026** Captura faltante no causará crash.

**RNF-02-027** DB corrupta/incompatible tendrá diagnóstico explícito.

**RNF-02-028** Modelos protocolo tipados con Pydantic.

**RNF-02-029** Identificadores de código en inglés.

**RNF-02-030** UI/documentación visible en español.

**RNF-02-031** No añadir `psutil` ni nueva dependencia monitorización.

**RNF-02-032** Polars fuera del pipeline crítico.

---

## 9. Reglas de negocio / dominio

**BR-02-001** `VisionReport = observación`, nunca autorización física.

**BR-02-002** Mobile decide; laptop informa; ESP32 ejecuta/protege.

**BR-02-003** Coordenadas externas = mm.

**BR-02-004** Persistencia/intercambio temporal = UTC.

**BR-02-005** Position oficial de VisionReport = filtered_position.

**BR-02-006** No detection invalida posición actual.

**BR-02-007** Detección no implica posición física si calibración no es válida.

**BR-02-008** Z continúa null.

**BR-02-009** Máximo un cliente Mobile activo.

**BR-02-010** Mobile puede start/stop visión, no hardware físico.

**BR-02-011** UI local y Mobile son orígenes válidos de start/stop.

**BR-02-012** Conexión WebSocket no inicia detector automáticamente.

**BR-02-013** Heartbeat es health del visor, no watchdog físico.

**BR-02-014** Report reemplazado antes de enviarse no se persiste como report emitido.

**BR-02-015** Capturas V1 = manuales.

**BR-02-016** V1 = sin auto-delete.

---

## 10. Modelo de estados

### 10.1. NetworkServerState

```text
STOPPED
STARTING
LISTENING
CLIENT_CONNECTED
STOPPING
ERROR
```

```text
STOPPED --bootstrap--> STARTING --success--> LISTENING
LISTENING --accept--> CLIENT_CONNECTED
CLIENT_CONNECTED --disconnect--> LISTENING
STARTING/LISTENING/CLIENT_CONNECTED --fatal--> ERROR
```

### 10.2. ClientState

```text
NONE
CONNECTING
ACTIVE
CLOSING
```

### 10.3. StorageState

```text
UNINITIALIZED
OPENING
READY
DEGRADED
ERROR
CLOSING
CLOSED
```

### 10.4. DatabaseHealth

```text
UNKNOWN
HEALTHY
DEGRADED
UNAVAILABLE
```

### 10.5. ReportDeliveryState

```text
IDLE
PENDING
SENDING
SENT
DROPPED_STALE
ERROR
```

---

## 11. Modelo de datos

### 11.1. ProtocolEnvelope

```text
protocol: Literal["blanquita-vision"]
version: int = 1
type: str
messageId: UUID
timestamp: datetime UTC
payload: object
```

### 11.2. VisionPositionPayload

```text
x: float?
y: float?
z: float?
angle: float?
unit: Literal["mm"]
```

NaN/Inf inválidos.

### 11.3. VisionReportPayload

```text
detected: bool
object: str
position: VisionPositionPayload
confidence: float
calibrationStatus: str
trackingState: str
frameSequence: int
observationTimestamp: datetime UTC
```

`object = "gancho"` expresa el objetivo del detector; `detected` expresa presencia/ausencia.

### 11.4. VisionHelloPayload

```text
server: "BLANQUITA Vision"
protocolVersion: 1
endpoint: "/vision"
```

### 11.5. VisionReadyPayload

```text
ready: bool
cameraState: str
pipelineState: str
calibrationStatus: str
```

### 11.6. VisionStatusPayload

```text
cameraState: str
pipelineState: str
detectionState: str?
trackingState: str?
calibrationStatus: str
pipelineFps: float?
lastObservationTimestamp: datetime?
```

### 11.7. VisionErrorPayload

```text
code: str
message: str
recoverable: bool
replyToMessageId: UUID?
```

No enviar stack trace completo a Mobile.

### 11.8. VisionHeartbeatPayload

```text
serverTime: datetime UTC
ready: bool
replyToMessageId: UUID?
```

### 11.9. CameraStatusPayload

```text
state: str
cameraId: str?
displayName: str?
width: int?
height: int?
reportedFps: float?
```

### 11.10. CalibrationStatusPayload

```text
status: str
calibrationId: str?
unit: "mm"
cameraId: str?
width: int?
height: int?
```

### 11.11. VisionStartPayload / Stop / Ping

```text
{}
```

No reciben parámetros físicos/motores.

### 11.12. VisionSessionRecord

```text
id: UUID
started_at_utc: datetime
ended_at_utc: datetime?
start_source: local_ui | mobile
end_reason: str?
camera_id: str?
width: int?
height: int?
```

### 11.13. PersistedDetection

```text
id
session_id?
frame_sequence
timestamp_utc
detected
object_name
confidence
bbox_x?
bbox_y?
bbox_w?
bbox_h?
centroid_u?
centroid_v?
tracking_state?
tracking_source?
raw_x_mm?
raw_y_mm?
filtered_x_mm?
filtered_y_mm?
z_mm?
calibration_id?
```

### 11.14. PersistedVisionReport

```text
message_id
session_id?
frame_sequence
envelope_timestamp_utc
observation_timestamp_utc
detected
object_name
x_mm?
y_mm?
z_mm?
angle?
confidence
calibration_status
tracking_state
payload_json
```

### 11.15. PersistedCalibration

```text
id
camera_id
width
height
unit = mm
homography_json
created_at_utc
status
invalidated_at_utc?
```

### 11.16. PersistedCalibrationPoint

```text
calibration_id
point_order 1..4
u
v
x_mm
y_mm
```

### 11.17. CaptureRecord

```text
id
session_id?
created_at_utc
relative_path
format: jpg | png
frame_sequence?
detected?
confidence?
x_mm?
y_mm?
z_mm?
```

### 11.18. MetricSample

Una fila por segundo por sesión activa:

```text
id
session_id
window_start_utc
window_end_utc
capture_fps_avg?
pipeline_fps_avg?
preprocess_ms_avg?
detection_ms_avg?
tracking_ms_avg?
position_ms_avg?
filter_ms_avg?
total_ms_avg?
confidence_avg?
detections_count
tracking_lost_count
reacquisitions_count
errors_count
raw_x_avg_mm?
raw_y_avg_mm?
filtered_x_avg_mm?
filtered_y_avg_mm?
```

### 11.19. EventRecord

```text
id
session_id?
timestamp_utc
category
event_type
severity
message
metadata_json?
```

### 11.20. ErrorRecord

```text
id
session_id?
timestamp_utc
component
code
message
recoverable
details_json?
```

---

## 12. Interfaces / Ports

### 12.1. ReportPublisherPort

```python
class ReportPublisherPort(Protocol):
    def publish_report(self, report: "VisionReport") -> None: ...
    def publish_status(self, status: "VisionStatus") -> None: ...
    def publish_error(self, error: "VisionError") -> None: ...
```

Application no deberá esperar bloqueo de red desde UI.

### 12.2. VisionRepositoryPort

```python
class VisionRepositoryPort(Protocol):
    def create_session(self, session: "VisionSessionRecord") -> None: ...
    def close_session(self, session_id: str, ended_at_utc, reason: str) -> None: ...
    def save_detection(self, record: "PersistedDetection") -> None: ...
    def save_report(self, record: "PersistedVisionReport") -> None: ...
    def save_metric_sample(self, sample: "MetricSample") -> None: ...
    def save_event(self, event: "EventRecord") -> None: ...
    def save_error(self, error: "ErrorRecord") -> None: ...
```

Además de consultas paginadas/filtradas.

### 12.3. PersistentCalibrationRepository

Implementa CalibrationRepositoryPort de SPEC-01 sin cambiar su semántica.

### 12.4. CaptureStoragePort

```python
class CaptureStoragePort(Protocol):
    def save_capture(self, capture: "CapturedFrame", format: str) -> "StoredCapture": ...
```

### 12.5. SettingsRepositoryPort

Persistencia de ajustes validados.

### 12.6. DiagnosticsProviderPort

Agrega snapshots camera/vision/network/database/filesystem/system sin requerir dependencias nuevas.

---

## 13. Adapters

### 13.1. WebSocketVisionServer

```text
ReportPublisherPort
        ↓
WebSocketVisionServer
        ↓
websockets 17.1
```

Responsabilidades:

- lifecycle;
- path;
- client exclusivity;
- parse/serialize;
- heartbeat;
- latest report pending;
- states;
- traducción de errores.

### 13.2. SQLiteVisionRepository

Implementa VisionRepositoryPort mediante `sqlite3`.

### 13.3. SQLiteCalibrationRepository

Implementa CalibrationRepositoryPort.

`InMemoryCalibrationRepository` se conserva para tests.

### 13.4. FileSystemCaptureStorage

Guarda JPG/PNG bajo capture root.

### 13.5. SystemDiagnosticsProvider

Usa stdlib/Qt/componentes aprobados. No `psutil`.

---

## 14. Flujo técnico

### 14.1. Percepción → red/persistencia

```text
Vision Worker
    ↓
VisionObservation
    ├───────────────┐
    ↓               ↓
Protocol Mapper   Storage Mapper
    ↓               ↓
VisionReport     Records
    ↓               ↓
Network Worker   Storage Worker
    ↓               ↓
Mobile           SQLite/filesystem
```

### 14.2. Latest-only

```text
Report 100 pending
Report 101 replaces 100 if 100 not sent
Report 102 replaces 101 if 101 not sent
        ↓
send 102
        ↓
persist 102 as emitted
```

### 14.3. Mobile → Application

```text
WebSocket
  ↓
JSON
  ↓
Pydantic
  ↓
Message Router
  ├── StartVision
  ├── StopVision
  └── Ping
```

### 14.4. Captura

```text
CapturedFrame
  ↓
Storage Worker
  ↓
JPG/PNG filesystem
  ↓ success
CaptureRecord SQLite
```

### 14.5. Calibración

```text
Calibration VALID
  ↓
SQLiteCalibrationRepository
  ↓
DB

restart
  ↓
camera+resolution known
  ↓
latest compatible valid calibration
  ↓
SPEC-01 pipeline
```

---

## 15. Concurrencia

### 15.1. Main/UI Thread

Solo presentación/interacción/resultados ligeros.

No ejecutará:

- socket loop;
- heartbeat loop;
- SQLite I/O bloqueante;
- encoding/escritura de captura;
- export pesado;
- query histórica grande.

### 15.2. Camera Worker

Heredado de SPEC-00.

### 15.3. Vision Worker

Heredado de SPEC-01.

### 15.4. Network Worker

Responsable de:

- server;
- client;
- RX/TX;
- heartbeat;
- latest pending report;
- network states.

### 15.5. Storage Worker

Responsable de:

- SQLite writes;
- filesystem capture;
- queries pesadas;
- export cuando corresponda.

### 15.6. Buffers/backpressure

VisionReport pending:

```text
capacidad lógica = 1
```

Storage queue deberá ser acotada/controlada.

No se permiten colas ilimitadas.

Los registros que no puedan persistirse no deberán descartarse silenciosamente.

### 15.7. Shutdown

```text
stop nuevas acciones
↓
close client
↓
stop server/heartbeat
↓
close active vision session
↓
drenar operaciones críticas storage de forma controlada
↓
close SQLite
↓
close workers
```

---

## 16. Manejo de errores

| Error | Reacción | Recuperación | Estado/log |
|---|---|---|---|
| Puerto ocupado | server no inicia | liberar/cambiar solo con autorización | ERROR |
| Path incorrecto | rechazar | usar /vision | WARNING |
| Segundo cliente | rechazar segundo | esperar cliente libre | WARNING |
| JSON malformado | vision.error, no acción | cliente corrige | WARNING |
| Envelope inválido | vision.error | cliente corrige | WARNING |
| Version incompatible | error + posible close | cliente compatible | WARNING |
| Start no válido | error de use case | corregir precondición | WARNING |
| Mobile desconecta | liberar sesión cliente | volver LISTENING | INFO |
| Send falla | marcar network error | esperar reconexión | WARNING |
| SQLite locked | DEGRADED/retry controlado | recuperar | WARNING |
| DB no abre | storage unavailable | intervención | ERROR |
| Schema incompatible | no escribir | diagnóstico/migración válida | ERROR |
| Capture path no writable | fallar captura | corregir permisos/path | ERROR |
| Capture file missing | mostrar faltante | no crash | WARNING |
| Export write falla | informar | elegir otra ruta | ERROR |
| Pydantic serialization falla | no enviar | corregir error interno | ERROR |
| NaN/Inf | rechazar report | invalidar resultado | ERROR |

Perder Mobile no deberá cerrar cámara, UI o control manual del sistema.

---

## 17. Observabilidad

### 17.1. Eventos de red

```text
network_server_starting
network_server_listening
network_server_error
mobile_connected
mobile_disconnected
second_client_rejected
protocol_message_invalid
vision_start_received
vision_stop_received
vision_ping_received
vision_report_sent
vision_report_dropped_stale
heartbeat_sent
```

### 17.2. Eventos storage

```text
database_opened
database_error
database_degraded
schema_initialized
schema_migrated
capture_saved
capture_save_failed
calibration_persisted
calibration_loaded
export_completed
export_failed
```

### 17.3. Métricas

- reports produced;
- reports sent;
- reports stale-dropped;
- send duration;
- storage queue depth;
- DB write errors;
- capture errors;
- metric samples persisted.

No afirmar RTT de red si el mecanismo no lo mide realmente.

---

## 18. UI/UX

### 18.1. Diseño

Mantener tema negro técnico de SPEC-00/01.

### 18.2. LIVE

Añadir sin sobrecargar:

```text
Mobile: Conectado/Desconectado
Vision Server: Listening/Error
Último TX
```

### 18.3. ANALÍTICA

Pantalla funcional con:

```text
TIEMPO REAL
HISTÓRICO
```

Métricas posibles:

- capture FPS;
- pipeline FPS;
- total ms;
- preprocess/detection/tracking/position ms;
- confidence;
- X/Y raw;
- X/Y filtered;
- detecciones;
- tracking lost;
- errores.

Histórico:

- selector sesión;
- rango temporal;
- series;
- tabla/resumen;
- loading;
- empty;
- error.

### 18.4. REPORTES

Categorías:

```text
Sesiones
Detecciones
VisionReports
Capturas
Calibraciones
Eventos
Errores
```

Funciones:

- filtros;
- detalle;
- abrir imagen;
- export JSON;
- export CSV.

UI muestra hora local; datos/export conservan UTC.

### 18.5. DIAGNÓSTICOS

#### CAMERA

- state;
- device;
- backend;
- resolution;
- FPS disponibles.

#### VISION

- pipeline;
- detector;
- tracker;
- calibration;
- FPS;
- latencias;
- last observation.

#### NETWORK

- bind;
- port;
- path;
- server state;
- client state;
- connected since;
- last RX/TX;
- heartbeat;
- last error.

#### DATABASE

- path;
- health;
- WAL;
- schema version;
- size;
- last error.

#### FILESYSTEM

- capture path;
- writable;
- format;
- last capture.

#### SYSTEM

- app version;
- Python version;
- OS;
- architecture;
- CPU/RAM/GPU solo si fiable con stack actual;
- si no: `No disponible`.

### 18.6. AJUSTES

SPEC-02 podrá habilitar configuración de:

- capture format;
- data path;
- analítica;
- logs;
- opciones network permitidas.

Baseline aprobado:

```text
bind = 0.0.0.0
port = 8765
path = /vision
protocol version = 1
```

---

## 19. Seguridad

### 19.1. Red

```text
ws://
sin autenticación
LAN privada
```

Consecuencias:

- no port-forwarding a Internet;
- no considerar canal seguro en red hostil;
- validar cada mensaje;
- un cliente máximo;
- cero comandos físicos.

### 19.2. Input

```text
text
↓
JSON
↓
Pydantic
↓
router
↓
use case
```

### 19.3. Filesystem

- filenames generados por app;
- Mobile no define paths;
- capture root controlado;
- evitar traversal;
- export path solo elegido localmente.

### 19.4. SQLite

- queries parametrizadas;
- foreign keys;
- transacciones;
- schema versioning.

### 19.5. Datos físicos

- null no se convierte a 0;
- confidence no autoriza movimiento;
- last-known-position no se presenta como actual.

---

## 20. Persistencia

### 20.1. Paths iniciales

```text
data/blanquita_vision.db
data/captures/
```

Respetar mecanismo de paths existente si ya fue implementado.

### 20.2. `schema_meta`

```text
key TEXT PRIMARY KEY
value TEXT NOT NULL
```

Incluye `schema_version`.

### 20.3. `app_settings`

```text
key TEXT PRIMARY KEY
value_json TEXT NOT NULL
updated_at_utc TEXT NOT NULL
```

### 20.4. `vision_sessions`

```text
session_id TEXT PRIMARY KEY
started_at_utc TEXT NOT NULL
ended_at_utc TEXT NULL
start_source TEXT NOT NULL
end_reason TEXT NULL
camera_id TEXT NULL
width INTEGER NULL
height INTEGER NULL
```

Índices: `started_at_utc`, `ended_at_utc`.

### 20.5. `calibrations`

```text
calibration_id TEXT PRIMARY KEY
camera_id TEXT NOT NULL
width INTEGER NOT NULL
height INTEGER NOT NULL
unit TEXT NOT NULL CHECK(unit='mm')
homography_json TEXT NOT NULL
created_at_utc TEXT NOT NULL
status TEXT NOT NULL
invalidated_at_utc TEXT NULL
```

Índice compuesto:

```text
(camera_id, width, height, status, created_at_utc)
```

### 20.6. `calibration_points`

```text
calibration_id TEXT NOT NULL
point_order INTEGER NOT NULL
u REAL NOT NULL
v REAL NOT NULL
x_mm REAL NOT NULL
y_mm REAL NOT NULL
PRIMARY KEY(calibration_id, point_order)
FOREIGN KEY(calibration_id) REFERENCES calibrations(calibration_id)
```

### 20.7. `detections`

```text
detection_id INTEGER PRIMARY KEY AUTOINCREMENT
session_id TEXT NULL
frame_sequence INTEGER NOT NULL
timestamp_utc TEXT NOT NULL
detected INTEGER NOT NULL
object_name TEXT NOT NULL
confidence REAL NOT NULL
bbox_x REAL NULL
bbox_y REAL NULL
bbox_w REAL NULL
bbox_h REAL NULL
centroid_u REAL NULL
centroid_v REAL NULL
tracking_state TEXT NULL
tracking_source TEXT NULL
raw_x_mm REAL NULL
raw_y_mm REAL NULL
filtered_x_mm REAL NULL
filtered_y_mm REAL NULL
z_mm REAL NULL
calibration_id TEXT NULL
```

Índices:

```text
(session_id, timestamp_utc)
timestamp_utc
detected
```

### 20.8. `vision_reports`

```text
message_id TEXT PRIMARY KEY
session_id TEXT NULL
frame_sequence INTEGER NOT NULL
envelope_timestamp_utc TEXT NOT NULL
observation_timestamp_utc TEXT NOT NULL
detected INTEGER NOT NULL
object_name TEXT NOT NULL
x_mm REAL NULL
y_mm REAL NULL
z_mm REAL NULL
angle REAL NULL
confidence REAL NOT NULL
calibration_status TEXT NOT NULL
tracking_state TEXT NOT NULL
payload_json TEXT NOT NULL
```

### 20.9. `captures`

```text
capture_id TEXT PRIMARY KEY
session_id TEXT NULL
created_at_utc TEXT NOT NULL
relative_path TEXT NOT NULL UNIQUE
format TEXT NOT NULL
frame_sequence INTEGER NULL
detected INTEGER NULL
confidence REAL NULL
x_mm REAL NULL
y_mm REAL NULL
z_mm REAL NULL
```

### 20.10. `metric_samples`

```text
metric_id INTEGER PRIMARY KEY AUTOINCREMENT
session_id TEXT NOT NULL
window_start_utc TEXT NOT NULL
window_end_utc TEXT NOT NULL
capture_fps_avg REAL NULL
pipeline_fps_avg REAL NULL
preprocess_ms_avg REAL NULL
detection_ms_avg REAL NULL
tracking_ms_avg REAL NULL
position_ms_avg REAL NULL
filter_ms_avg REAL NULL
total_ms_avg REAL NULL
confidence_avg REAL NULL
detections_count INTEGER NOT NULL DEFAULT 0
tracking_lost_count INTEGER NOT NULL DEFAULT 0
reacquisitions_count INTEGER NOT NULL DEFAULT 0
errors_count INTEGER NOT NULL DEFAULT 0
raw_x_avg_mm REAL NULL
raw_y_avg_mm REAL NULL
filtered_x_avg_mm REAL NULL
filtered_y_avg_mm REAL NULL
```

Índice: `(session_id, window_start_utc)`.

### 20.11. `events`

```text
event_id INTEGER PRIMARY KEY AUTOINCREMENT
session_id TEXT NULL
timestamp_utc TEXT NOT NULL
category TEXT NOT NULL
event_type TEXT NOT NULL
severity TEXT NOT NULL
message TEXT NOT NULL
metadata_json TEXT NULL
```

### 20.12. `errors`

```text
error_id INTEGER PRIMARY KEY AUTOINCREMENT
session_id TEXT NULL
timestamp_utc TEXT NOT NULL
component TEXT NOT NULL
code TEXT NOT NULL
message TEXT NOT NULL
recoverable INTEGER NOT NULL
details_json TEXT NULL
```

### 20.13. Retención

V1:

```text
NO DELETE automático
NO limpieza por días
NO limpieza por tamaño
NO borrado automático de capturas
```

---

## 21. Testing obligatorio

### TC-02-001 — Envelope válido

Mensaje Pydantic válido → parse exitoso. Tipo: UNIT.

### TC-02-002 — Protocol incorrecto

Rechazo. Tipo: NEGATIVE.

### TC-02-003 — Version incompatible

Error explícito; ninguna acción. Tipo: NEGATIVE.

### TC-02-004 — UUID inválido

Rechazo. Tipo: NEGATIVE.

### TC-02-005 — Timestamp naive remoto

Rechazo. Tipo: NEGATIVE.

### TC-02-006 — Normalización UTC

Timestamp aware permitido → serialización canónica UTC/Z. Tipo: UNIT.

### TC-02-007 — Report calibrado

Filtered X/Y mm; Z null. Tipo: UNIT.

### TC-02-008 — Report no detectado

Posición null. Tipo: UNIT.

### TC-02-009 — Detección sin calibración

Detected true + posición física null. Tipo: UNIT.

### TC-02-010 — NaN/Inf

Rechazo. Tipo: NEGATIVE.

### TC-02-011 — Server endpoint

Escucha 0.0.0.0:8765 y acepta /vision. Tipo: INTEGRATION.

### TC-02-012 — Path incorrecto

Rechazo. Tipo: NEGATIVE.

### TC-02-013 — Cliente único

Cliente A permanece; B rechazado. Tipo: INTEGRATION.

### TC-02-014 — Hello/ready

Conexión recibe modelos válidos. Tipo: INTEGRATION.

### TC-02-015 — vision.start

Inicia pipeline cuando precondiciones permiten. Tipo: INTEGRATION.

### TC-02-016 — start idempotente

No crea worker/sesión duplicada. Tipo: EDGE.

### TC-02-017 — vision.stop

Detiene percepción sin acción física. Tipo: INTEGRATION.

### TC-02-018 — stop idempotente

Tipo: EDGE.

### TC-02-019 — ping

Heartbeat inmediato con replyToMessageId. Tipo: INTEGRATION.

### TC-02-020 — heartbeat periódico

Cadencia 2 s dentro de tolerancia scheduler del test. Tipo: ASYNC.

### TC-02-021 — stale contract

Contrato documenta 6 s. Tipo: CONTRACT.

### TC-02-022 — Mobile disconnect

Server vuelve LISTENING; visión local continúa. Tipo: INTEGRATION.

### TC-02-023 — Backpressure report

Productor rápido + socket lento → pending máximo 1. Tipo: PERFORMANCE/INTEGRATION.

### TC-02-024 — Persistir solo report emitido

Stale reemplazados no aparecen como emitidos. Tipo: INTEGRATION.

### TC-02-025 — Crear DB

Schema completo/versionado. Tipo: DATABASE.

### TC-02-026 — WAL

Modo WAL confirmado cuando soportado. Tipo: DATABASE.

### TC-02-027 — Foreign keys

Integridad esperada. Tipo: DATABASE.

### TC-02-028 — Session lifecycle

Start/end/reason correctos. Tipo: INTEGRATION.

### TC-02-029 — Start source local

`local_ui`. Tipo: UNIT/INTEGRATION.

### TC-02-030 — Start source mobile

`mobile`. Tipo: INTEGRATION.

### TC-02-031 — Calibration persist

Perfil + cuatro puntos. Tipo: DATABASE.

### TC-02-032 — Calibration reload compatible

Misma cámara/resolución carga perfil válido más reciente. Tipo: INTEGRATION.

### TC-02-033 — Calibration incompatible camera

No activa perfil. Tipo: NEGATIVE.

### TC-02-034 — Calibration incompatible resolution

No activa perfil. Tipo: NEGATIVE.

### TC-02-035 — Persist invalidation

Restart no reactiva inválida. Tipo: DATABASE.

### TC-02-036 — JPG capture

Archivo + row. Tipo: FILESYSTEM.

### TC-02-037 — PNG capture

Archivo + row. Tipo: FILESYSTEM.

### TC-02-038 — No automatic capture

Detecciones sin click → cero archivos. Tipo: NEGATIVE.

### TC-02-039 — Capture write failure

No registrar éxito. Tipo: NEGATIVE.

### TC-02-040 — Path traversal

Entrada externa no escapa capture root. Tipo: SECURITY.

### TC-02-041 — Metric aggregation 1s

Agrega por ventana, no frame. Tipo: UNIT/INTEGRATION.

### TC-02-042 — Analytics real-time

No bloquea pipeline. Tipo: UI INTEGRATION.

### TC-02-043 — Analytics historical

Consulta por sesión/rango. Tipo: DATABASE/UI.

### TC-02-044 — Reports sessions

Listado/filtro/detalle. Tipo: UI.

### TC-02-045 — Reports detections/reports

Listado y detalle. Tipo: UI.

### TC-02-046 — Reports captures

Abre existente; missing controlado. Tipo: UI/FILESYSTEM.

### TC-02-047 — Export JSON

UTC, mm, null preservado. Tipo: INTEGRATION.

### TC-02-048 — Export CSV

Columnas estables y null consistente. Tipo: INTEGRATION.

### TC-02-049 — Diagnostics network

Server/client/RX/TX/heartbeat visibles. Tipo: UI.

### TC-02-050 — Diagnostics database

Path/health/WAL/schema visibles. Tipo: UI.

### TC-02-051 — Unavailable system metrics

No inventa CPU/RAM/GPU; muestra No disponible. Tipo: UI/NEGATIVE.

### TC-02-052 — Storage Worker no bloquea UI

Fake repository lento. Tipo: CONCURRENCY.

### TC-02-053 — Network Worker no bloquea UI

Tipo: CONCURRENCY.

### TC-02-054 — DB locked

DEGRADED/error explícito, no crash global. Tipo: FAULT INJECTION.

### TC-02-055 — DB unavailable

Percepción/red continúan cuando sea posible; storage falla explícitamente. Tipo: FAULT INJECTION.

### TC-02-056 — Malformed client message

No ejecuta start/stop. Tipo: SECURITY.

### TC-02-057 — Physical command rejected

`{"command":"d"}` o equivalente no pertenece al protocolo; ningún canal ESP32. Tipo: SECURITY.

### TC-02-058 — Offline LAN

Sin Internet, Laptop-Mobile funciona por LAN. Tipo: TEST CON RED REAL. Estado inicial: PENDIENTE.

### TC-02-059 — Mobile real interoperability

Hello/ready/status/report/heartbeat parseables por app real. Tipo: TEST CON DISPOSITIVO REAL. Estado inicial: PENDIENTE.

### TC-02-060 — Stale real

Interrumpir servidor/red y Mobile detecta stale según contrato 6 s. Tipo: TEST CON MOBILE REAL. Estado inicial: PENDIENTE.

### TC-02-061 — Benchmark WebSocket

Medir production/send/drop/send-duration/estabilidad. Umbrales: TBD. Tipo: PERFORMANCE.

### TC-02-062 — Benchmark SQLite

Medir writes/query times/DB growth/queue. Umbrales: TBD. Tipo: PERFORMANCE.

### TC-02-063 — No-delete V1

No existe job automático destructivo. Tipo: ARCHITECTURE/INTEGRATION.

---

## 22. Criterios de aceptación

**AC-02-001** DADA la app iniciada, CUANDO puerto está libre, ENTONCES server escucha en `0.0.0.0:8765/vision`.

**AC-02-002** DADO server libre, CUANDO Mobile conecta, ENTONCES recibe hello/ready/estado.

**AC-02-003** DADO cliente activo, CUANDO conecta segundo, ENTONCES segundo se rechaza sin desplazar primero.

**AC-02-004** DADO start remoto válido, CUANDO visión puede iniciar, ENTONCES usa el mismo caso de uso que UI local sin autoridad física.

**AC-02-005** DADO estado ya coincidente, CUANDO start/stop se repite, ENTONCES es idempotente.

**AC-02-006** DADO cliente activo, CUANDO transcurre operación, ENTONCES heartbeat se emite cada 2 s según política aprobada.

**AC-02-007** DADA VisionObservation, CUANDO crea VisionReport, ENTONCES usa filtered_position, mm, X/Y válidos cuando corresponda y Z null.

**AC-02-008** DADO objeto no detectado, CUANDO reporta, ENTONCES no reutiliza posición anterior.

**AC-02-009** DADA red más lenta que visión, CUANDO varios reports quedan pendientes, ENTONCES solo se conserva el último.

**AC-02-010** DADO report realmente enviado, CUANDO storage está READY, ENTONCES queda persistido con messageId/payload.

**AC-02-011** DADA Calibration VALID, CUANDO se aplica, ENTONCES se guarda con cámara/resolución/homografía/4 puntos/mm.

**AC-02-012** DADA app reiniciada y cámara/resolución compatibles, CUANDO existe perfil válido, ENTONCES se carga automáticamente sin afirmar geometría física intacta.

**AC-02-013** DADA captura manual, CUANDO formato JPG/PNG está seleccionado, ENTONCES archivo va a filesystem y metadata a SQLite.

**AC-02-014** DADAS detecciones sin acción manual, CUANDO operan, ENTONCES no se crean imágenes automáticamente.

**AC-02-015** DADA sesión activa, CUANDO transcurre operación, ENTONCES métricas históricas se agregan a 1 muestra/s y no por frame.

**AC-02-016** DADOS datos, CUANDO abre ANALÍTICA, ENTONCES se visualizan sin detener pipeline.

**AC-02-017** DADOS datos, CUANDO abre REPORTES, ENTONCES puede consultar/filtrar/exportar JSON/CSV.

**AC-02-018** DADOS componentes, CUANDO abre DIAGNÓSTICOS, ENTONCES muestra estados reales y `No disponible` donde no haya dato fiable.

**AC-02-019** DADO timestamp persistido/intercambiado, CUANDO se inspecciona, ENTONCES está UTC; conversión local solo UI.

**AC-02-020** DADO contenido remoto fuera de protocolo, CUANDO valida, ENTONCES se rechaza y nunca alcanza ESP32.

---

## 23. Definition of Done

```text
✓ modelos Pydantic protocolo v1
✓ UTC transversal
✓ unidad mm
✓ WebSocketVisionServer
✓ 0.0.0.0:8765/vision
✓ un cliente activo
✓ hello/ready/status/report/error
✓ heartbeat 2 s
✓ stale contract 6 s
✓ start/stop/ping
✓ idempotencia start/stop
✓ latest-only outbound
✓ filtered_position oficial
✓ Z null
✓ SQLite schema versionado
✓ WAL
✓ VisionRepositoryPort
✓ SQLiteVisionRepository
✓ Network Worker
✓ Storage Worker
✓ vision sessions
✓ detections persistence
✓ emitted reports persistence
✓ calibration persistence/reload
✓ metric sample 1/s
✓ events/errors
✓ manual capture JPG/PNG
✓ filesystem sin BLOB
✓ ANALÍTICA funcional
✓ REPORTES funcional
✓ export JSON/CSV
✓ DIAGNÓSTICOS funcional
✓ settings SPEC-02 persistibles
✓ no auto-delete
✓ no psutil
✓ no ONNX/GPU adelantado
✓ sin auth/TLS inventados
✓ LAN-only documentado
✓ no control ESP32
✓ tests pasan
✓ documentación actualizada
✓ sin operaciones Git por agentes
```

### 23.1. VALIDADO EN SOFTWARE

Requiere protocol, async WebSocket, DB, filesystem, UI integration, concurrency y fault tests.

### 23.2. VALIDADO EN RED/DISPOSITIVO REAL

Requiere Mobile real, Wi-Fi/LAN real, interoperabilidad, heartbeat/stale, desconexión/reconexión y operación sin Internet.

No declarar interoperabilidad Mobile validada solo con fake client.

---

## 24. Dependencias con otras SPECS

### DEPENDE DE SPEC-00

Consume cámara, CapturedFrame, UI base, lifecycle y logging.

### DEPENDE DE SPEC-01

Consume:

```text
Detection
TrackingResult
Calibration
CalibrationRepositoryPort
PositionEstimate
VisionObservation
VisionPipelineController
estados/métricas
```

NO modifica:

- HSV/contornos;
- score;
- CSRT;
- reacquisición;
- homografía;
- EMA;
- X/Y/Z;
- Z=null.

### DESBLOQUEA SPEC-03

Entrega protocolo, red, storage, histórico, métricas, diagnósticos, reportes e integración.

SPEC-03 se centrará en:

```text
IA/ONNX
testing integral
performance final
tolerancia a fallos final
release Windows
```

### NO DEBE MODIFICAR

- detector OpenCV aprobado;
- pipeline físico;
- autoridad Mobile;
- control ESP32;
- release final.

---

## 25. Decisiones abiertas

### OPEN-02-001 — Validación física heredada de SPEC-01

**Pregunta:** valores HSV/área/confidence/alpha y precisión real.

**Motivo:** dependen del hardware.

**Impacto:** calidad de reports transportados/persistidos.

**Resolver:** validación física SPEC-01 antes de automatización real.

### OPEN-02-002 — Autenticación/TLS futura

**Pregunta:** token/WSS en una versión futura.

**Motivo:** V1 = LAN privada sin auth.

**Resolver:** si se requiere red no confiable/exposición externa.

### OPEN-02-003 — Retención futura

**Pregunta:** límite por días/tamaño/archivo.

**Motivo:** V1 conserva todo.

**Resolver:** cuando mediciones reales justifiquen política.

### OPEN-02-004 — Métricas completas del sistema

**Pregunta:** autorizar psutil o API Windows futura.

**Motivo:** CPU/RAM/GPU detallados pueden no ser obtenibles con stack actual.

**Resolver:** SPEC-03/evolución posterior si realmente necesario.

---

## 26. Riesgos

### RISK-02-001 — WebSocket sin autenticación

Impacto alto en red hostil. Mitigación: LAN privada, no Internet, un cliente, validación estricta.

### RISK-02-002 — ws:// sin cifrado

Mitigación: LAN confiable; WSS futuro.

### RISK-02-003 — Alta tasa de reports

Mitigación: latest-only, persistir emitidos, benchmark.

### RISK-02-004 — Crecimiento SQLite

Probabilidad alta con uso prolongado. Mitigación: índices, métricas 1/s, medir crecimiento, retención futura.

### RISK-02-005 — Crecimiento filesystem

Mitigación: captura solo manual V1.

### RISK-02-006 — Storage lento

Mitigación: worker, cola acotada, DEGRADED, benchmark.

### RISK-02-007 — DB locked/corrupta

Mitigación: WAL, transacciones, diagnostics, manejo explícito.

### RISK-02-008 — Convención antigua en Mobile

Documentación móvil previa mostraba X/Z; SPEC-01/02 establecen X/Y y Z=null. Mitigación: contrato SPEC-02 prevalece para integración y Mobile deberá actualizar modelos/UI.

### RISK-02-009 — Timestamp inconsistente

Mitigación: UTC obligatorio end-to-end.

### RISK-02-010 — Persistencia de reports a alta frecuencia

Mitigación: benchmark de DB y latest-only de red.

### RISK-02-011 — Auto-load calibration tras movimiento físico

Mitigación: match camera/resolution + obligación operacional de recalibrar si cambió geometría.

---

## 27. Trazabilidad

| Requisito | Caso de uso | Test | Criterio |
|---|---|---|---|
| RF-02-001..014 | UC-02-04..12 | TC-02-001..010,056 | AC-02-004/005/019/020 |
| RF-02-015..028 | UC-02-02..07 | TC-02-014..021 | AC-02-002/004/005/006 |
| RF-02-029..042 | UC-02-01..03 | TC-02-011..014,058 | AC-02-001..003 |
| RF-02-043..046 | UC-02-06/07 | TC-02-019..021,060 | AC-02-006 |
| RF-02-047..065 | UC-02-08..11 | TC-02-007..010 | AC-02-007/008 |
| RF-02-066..069 | UC-02-08 | TC-02-023/024/061 | AC-02-009/010 |
| RF-02-070..078 | UC-02-13..23 | TC-02-025..027/052/054/055 | AC-02-010/016/017/018 |
| RF-02-079..084 | UC-02-13/14 | TC-02-028..030 | AC-02-010 |
| RF-02-085..091 | UC-02-08/13/14 | TC-02-024/028 | AC-02-010 |
| RF-02-092..101 | UC-02-15/16 | TC-02-031..035 | AC-02-011/012 |
| RF-02-102..111 | UC-02-17 | TC-02-036..040/046 | AC-02-013/014 |
| RF-02-112..117 | UC-02-18/19 | TC-02-041..043 | AC-02-015/016 |
| RF-02-118..121 | varios | TC-02-054..057 | AC-02-018/020 |
| RF-02-122..125 | ajustes | settings tests | AC-02-001/013 |
| RF-02-126..128 | storage | TC-02-063 | AC-02-017 |
| RF-02-129..138 | UC-02-19 | TC-02-042/043 | AC-02-016 |
| RF-02-139..151 | UC-02-20..22 | TC-02-044..048 | AC-02-017 |
| RF-02-152..165 | UC-02-23 | TC-02-049..051 | AC-02-018 |
| RNF-02-001..005 | todos | architecture tests | AC-02-020 |
| RNF-02-006..009 | todos | TC-02-052/053 | AC-02-001/016 |
| RNF-02-010..013 | UC-02-08/19 | TC-02-023/061/062 | AC-02-009/016 |
| RNF-02-014..018 | protocol/storage | TC-02-001/025/047/048 | AC-02-010/019 |
| RNF-02-019..023 | network/security | TC-02-056..058 | AC-02-020 |
| RNF-02-024..027 | faults | TC-02-022/046/054/055 | AC-02-018 |
| RNF-02-028..032 | todos | static/architecture | AC-02-018/020 |

---

## 28. Registro de implementación y verificación

### 28.1. Entrega funcional

Se implementaron modelos Pydantic, envelope/payload estrictos, UTC/Z, conversión exacta de mm/cm/m a mm, Report Mapper, ReportPublisherPort, WebSocketVisionServer, Network Worker, SQLiteVisionRepository, SQLiteCalibrationRepository con caché síncrona e I/O asíncrono, Storage Worker, capturas filesystem, ajustes, sesiones, agregación métrica y coordinación de shutdown.

El servidor inicia automáticamente, acepta /vision y un cliente activo, emite hello/ready/status/heartbeat y enruta start/stop/ping al controlador existente. El envío tiene capacidad de un reporte pendiente reemplazable y se registran como emitidos solo envíos completados, con su sesión original. No se introduce ACK, vision.pong ni control físico.

SQLite utiliza WAL, foreign keys, transacciones y schema versionado. Un schema desconocido/incompatible se rechaza sin migración improvisada ni sobrescritura. Los ajustes se validan antes de aplicarse. Invalidaciones y cuatro puntos se persisten; una carga tardía no revierte una invalidación manual. La unidad UI de nuevas calibraciones es mm.

ANALÍTICA, REPORTES, DIAGNÓSTICOS y AJUSTES son funcionales; LIVE muestra red y permite guardar capturas manuales. Se mantiene el detalle de calibración con puntos, exportación completa de filas filtradas, timestamps originales UTC y conversión local solo de presentación. Consultas y series históricas se paginan a 50 filas; el usuario ve explícitamente la página graficada.

Storage controla 256 trabajos con 192 ordinarios y reserva de 64, y dos capturas pendientes. Rechazos/fallos se muestran y contabilizan; no se promete persistencia de trabajos no aceptados. Los registros y archivos no se eliminan automáticamente. Un archivo con fallo posterior de metadata se conserva y se informa como operación incompleta.

### 28.2. Verificación en software

**Fecha de registro:** 6 de octubre de 2026.

```text
.venv\Scripts\python.exe -m pytest -q
161 passed, 1 skipped
```

La suite cubre contrato estricto, UUID, timezone-aware/UTC, unidades, filtered_position, null y NaN/Inf; WebSocket real en loopback mediante cliente Python, path, exclusividad, hello/ready, ping/heartbeat, mensajes inválidos/binarios/oversized y latest-only con socket simulado lento; SQLite/schema/WAL/foreign keys, sesiones/origen, calibración/reload/invalidation, JPG/PNG, fallos de archivo/metadata, exportación y UI.

También cubre saturación y responsividad de Storage Worker, DB locked/unavailable, continuidad de percepción, prevención de sesión/worker duplicados, origen mobile heredado durante reinicios, carga tardía descartada y cierre coordinado. Se conservan las regresiones de SPEC-00 y SPEC-01; el test temporal de backpressure utiliza una barrera determinista, no una suposición sobre la velocidad del scheduler.

La omisión corresponde al test opcional de cámara física de SPEC-00, que requiere índice explícito. No se utilizó Mobile real ni el cartesiano. Los scripts tests/benchmark_network.py y tests/benchmark_storage.py se comprobaron en ejecuciones breves sintéticas; no se acreditan objetivos ni benchmark de operación real.

### 28.3. Estado y seguimiento

**Estado documental: IMPLEMENTED. VALIDADO EN SOFTWARE** para los escenarios registrados. No se declara VALIDATED en red/dispositivo real.

Pendientes TC-02-058/059/060: Wi-Fi/LAN real sin Internet, interoperabilidad de BLANQUITA Mobile real y detección de stale a seis segundos. Los benchmarks TC-02-061/062 requieren registrar mediciones representativas; objetivos continúan TBD. El histórico se conserva indefinidamente, con crecimiento pendiente de medir.

La validación física de SPEC-01 sigue pendiente y la limitación USB con DSHOW de SPEC-00 se hereda. Calibración VALID significa estado matemático/operativo del perfil, no certificación de precisión física ni autorización de movimiento. No se inicia SPEC-03 automáticamente.

---

# Anexo A — Decisiones cerradas

```text
DEC-02-001
Se avanza usando contratos software de SPEC-01 aunque hardware siga pendiente.

DEC-02-002
Unidad global = mm.

DEC-02-003
Timestamps persistidos/intercambiados = UTC ISO-8601 aware.
UI localiza solo al presentar.

DEC-02-004
VisionReport robusto: position + calibrationStatus + trackingState + frameSequence.

DEC-02-005
Position oficial = filtered_position.

DEC-02-006
No detection => position null.
Detected sin calibration => physical null.
Detected + calibration => X/Y; Z null.

DEC-02-007
Report por VisionObservation con latest-only ante backpressure.

DEC-02-008
UI local + Mobile pueden start/stop visión.
Conectar no inicia detector.

DEC-02-009
Server automático, 0.0.0.0:8765/vision, un cliente.

DEC-02-010
V1 sin autenticación, LAN privada.

DEC-02-011
Heartbeat 2 s, stale contractual 6 s.

DEC-02-012
Persistir reportes emitidos/eventos/errores/sesiones/calibraciones.
Métricas agregadas 1/s.

DEC-02-013
SQLite WAL + Storage Worker.

DEC-02-014
Solo captura manual V1.

DEC-02-015
Captura JPG o PNG seleccionable.

DEC-02-016
Calibration VALID se persiste; auto-load por camera_id + resolución.

DEC-02-017
Sin eliminación automática V1.

DEC-02-018
Diagnósticos sin nueva dependencia de monitorización.
```

---

# Anexo B — Contrato JSON V1

## B.1. Envelope

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.report",
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-10-06T15:30:00.123Z",
  "payload": {}
}
```

## B.2. VisionReport calibrado

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.report",
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-10-06T15:30:00.123Z",
  "payload": {
    "detected": true,
    "object": "gancho",
    "position": {
      "x": 145.2,
      "y": 78.4,
      "z": null,
      "angle": null,
      "unit": "mm"
    },
    "confidence": 0.96,
    "calibrationStatus": "VALID",
    "trackingState": "TRACKING",
    "frameSequence": 1842,
    "observationTimestamp": "2026-10-06T15:30:00.101Z"
  }
}
```

Los números son ejemplos de esquema, no mediciones reales ni precisión aprobada.

## B.3. Sin calibración

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.report",
  "messageId": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2026-10-06T15:30:01.123Z",
  "payload": {
    "detected": true,
    "object": "gancho",
    "position": {
      "x": null,
      "y": null,
      "z": null,
      "angle": null,
      "unit": "mm"
    },
    "confidence": 0.91,
    "calibrationStatus": "UNCALIBRATED",
    "trackingState": "TRACKING",
    "frameSequence": 1843,
    "observationTimestamp": "2026-10-06T15:30:01.101Z"
  }
}
```

---

# Anexo C — Matriz de mensajes

| type | Dirección | Trigger | Persistencia |
|---|---|---|---|
| vision.hello | Laptop → Mobile | connect | evento |
| vision.ready | Laptop → Mobile | connect/state | evento opcional |
| vision.status | Laptop → Mobile | cambios | evento opcional |
| vision.report | Laptop → Mobile | observation | sí, si enviado |
| vision.error | Laptop → Mobile | error | sí |
| vision.heartbeat | Laptop → Mobile | 2 s / ping | no fila obligatoria |
| camera.status | Laptop → Mobile | cambio cámara | evento |
| calibration.status | Laptop → Mobile | cambio calibration | evento |
| vision.start | Mobile → Laptop | control visión | evento |
| vision.stop | Mobile → Laptop | control visión | evento |
| vision.ping | Mobile → Laptop | health | no histórico obligatorio |

---

# Anexo D — Estructura esperada

```text
src/blanquita_vision/
├── domain/
│   ├── models/
│   │   ├── protocol.py
│   │   ├── report.py
│   │   ├── session.py
│   │   ├── metric.py
│   │   └── diagnostics.py
│   └── ports/
│       ├── report_publisher_port.py
│       ├── vision_repository_port.py
│       ├── calibration_repository_port.py
│       ├── capture_storage_port.py
│       ├── settings_repository_port.py
│       └── diagnostics_provider_port.py
├── application/
│   ├── report_mapper.py
│   ├── network_controller.py
│   ├── storage_controller.py
│   ├── analytics_service.py
│   ├── reports_service.py
│   └── diagnostics_service.py
├── adapters/
│   ├── network/
│   │   └── websocket_vision_server.py
│   └── storage/
│       ├── sqlite_vision_repository.py
│       ├── sqlite_calibration_repository.py
│       └── filesystem_capture_storage.py
├── infrastructure/
│   ├── database.py
│   ├── schema.py
│   └── health.py
└── presentation/
    ├── screens/
    │   ├── analytics_screen.py
    │   ├── reports_screen.py
    │   ├── diagnostics_screen.py
    │   └── settings_screen.py
    └── workers/
        ├── network_worker.py
        └── storage_worker.py
```

Orientativa; evitar clases redundantes.

---

# Anexo E — Interoperabilidad Mobile

Mobile deberá alinear su cliente con:

```text
protocol = blanquita-vision
version = 1
ws://IP_LAPTOP:8765/vision
heartbeat = 2 s
stale = 6 s
unidad = mm
X = horizontal
Y = vertical
Z = profundidad
Z actual = null
```

El documento móvil anterior que mostraba principalmente X/Z deberá actualizar su modelo/presentación durante la integración.

Mobile puede enviar:

```text
vision.start
vision.stop
vision.ping
```

No obtiene por este canal:

```text
comandos de motor
comandos crudos ESP32
acceso filesystem
acceso directo DB
```

---

# Revisión de completitud

```text
✓ SPEC-00 considerada
✓ SPEC-01 revisada
✓ avance sobre SPEC-01 autorizado
✓ protocolo versionado
✓ Pydantic
✓ UTC transversal
✓ unidad mm
✓ X/Y/Z actualizado
✓ VisionReport robusto
✓ filtered_position oficial
✓ WebSocket server
✓ endpoint
✓ cliente único
✓ heartbeat/stale
✓ start/stop/ping
✓ idempotencia
✓ latest-only
✓ SQLite/WAL/schema
✓ Storage Worker
✓ Network Worker
✓ sesiones
✓ calibraciones persistentes
✓ auto-load compatible
✓ reportes/detecciones
✓ captures filesystem JPG/PNG
✓ no BLOB
✓ métricas 1/s
✓ eventos/errores
✓ retención V1
✓ ANALÍTICA
✓ REPORTES
✓ DIAGNÓSTICOS
✓ sin psutil
✓ sin ONNX/GPU adelantado
✓ seguridad LAN
✓ tests
✓ acceptance criteria
✓ DoD
✓ riesgos
✓ trazabilidad
```

---

# Estado final

```text
SPEC-02
Protocolo, WebSocket, persistencia, analítica, reportes y diagnósticos

ESTADO: IMPLEMENTED

DEPENDENCIAS:
SPEC-00 VALIDATED
SPEC-01 APPROVED + implementación funcional validada en software

SIGUIENTE PASO:
Implementación entregada y validada en software (sección 28).
Completar pruebas con Mobile/LAN reales y mediciones representativas.

DESBLOQUEA TRAS IMPLEMENTACIÓN/VALIDACIÓN:
SPEC-03 — IA/ONNX, testing, rendimiento,
tolerancia a fallos y release Windows.

NO IMPLEMENTAR SPEC-03 AUTOMÁTICAMENTE.
```

## Políticas operativas aprobadas para implementación

El usuario aprobó SPEC-02 y las políticas siguientes antes de implementar:

- Unidad oficial mm. Conversiones exactas permitidas: mm, cm y m; otras unidades se rechazan sin reinterpretarlas.
- ready requiere cámara STREAMING, frame válido, parámetros/alpha aplicados y visión no ERROR/STOPPING.
- Start en STARTING/RUNNING es idempotente; durante STOPPING responde busy. Reinicios internos conservan el origen de inicio.
- Storage máximo 256 trabajos; hasta 192 ordinarios y 64 plazas reservadas a críticos. Detección por observación recibida; máximo dos capturas pendientes. Saturación y fallos se informan con estado/contadores, sin éxito ficticio ni descarte silencioso.
- SQLite: espera de bloqueo 0,1 s; hasta tres intentos separados por 0,2 s.
- Red: mensajes máximo 64 KiB, envío timeout tres segundos y cierre de cliente dos segundos. JSON/payload inválido informa error sin acción y mantiene conexión; protocolo/versión incompatibles o binario cierran conexión.
- CSV representa null con campo vacío; JSON conserva null.
- Si el archivo de captura se escribe pero falla metadata, se conserva y se informa el fallo, sin borrado automático.
- --data-dir selecciona la ruta de datos al arrancar. AJUSTES permite cambiar formato/ruta de capturas y muestra la ruta de DB.
- Gráficas en tiempo real: ventana de 120 s. Consultas paginadas de 50 filas.
- Cierre: espera asíncrona de cinco segundos; si quedan operaciones activas, mantener ventana abierta con diagnóstico.

Estos valores son límites iniciales de operación, no objetivos ni mediciones de benchmark.
