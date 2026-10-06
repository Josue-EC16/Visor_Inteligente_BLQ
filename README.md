# BLANQUITA Vision

Consola desktop Windows de percepción visual. La laptop percibe, el móvil decide
y el ESP32 ejecuta y protege.

## Implementación actual: SPEC-00, SPEC-01 y SPEC-02

**Estado documental:** VALIDATED — SPEC-00 terminada y validada por aceptación
expresa del usuario. La validación de software está completada y el usuario
confirmó el flujo funcional con cámara real, frontend y cierre/reapertura.
La retirada física USB con DSHOW conserva una limitación conocida aceptada
(INC-00-001 / DEC-00-014), recuperable manualmente. El benchmark no se ejecutó;
el alcance y seguimiento se registran al final del documento.

**SPEC-01:** implementación funcional disponible y validación de software registrada;
la SPEC permanece APPROVED mientras se completan tuning y pruebas con el gancho real.

**SPEC-02:** IMPLEMENTED y validada en software. La interoperabilidad con Mobile
real y la operación por Wi-Fi/LAN real siguen pendientes de pruebas independientes.

- Ventana maximizada, redimensionable, tema negro y sidebar de siete módulos.
- Inicio en LIVE con cámara desconectada.
- Descubrimiento manual por índices 0–9 y selección explícita.
- Captura fuera del hilo de UI mediante CameraPort/OpenCvCamera y worker Qt.
- Video PyQtGraph, resolución efectiva, backend, FPS reportado y FPS medido.
- Buffer de un frame vigente y notificaciones coalescidas sin imágenes encoladas.
- Captura manual JPG/PNG desde un snapshot independiente, con archivo y metadata SQLite.
- Recuperación de cámara limitada y reintento manual.
- Cierre asíncrono con liberación de cámara y worker.
- Barra inferior sincronizada con el estado de cámara en todas las pantallas.

SPEC-01 añade CALIBRACIÓN y DETECCIÓN funcionales, Vision Worker y overlays en LIVE.
SPEC-02 habilita ANALÍTICA, REPORTES, DIAGNÓSTICOS y AJUSTES, almacenamiento
SQLite/filesystem y servidor WebSocket automático.

**Convención vigente de SPEC-01, autorizada por el usuario:** X horizontal,
Y vertical y Z profundidad. La homografía estima X/Y; Z y angle permanecen
no disponibles (`null`). Esta convención sustituye la anterior para la percepción
actual; los documentos base anteriores no se han actualizado automáticamente.

## Baseline y entorno

Windows 10/11 x64, Python **3.13.16**, uv **0.12.22**.

| Dependencia | Versión |
|---|---|
| PySide6 | 6.11.2 |
| PyQtGraph | 0.14.0 |
| NumPy | 2.5.3 |
| opencv-contrib-python-headless | 4.14.0.94 |
| pytest (desarrollo) | 9.1.1 |
| Pydantic | 2.13.5 |
| websockets | 17.1 |

Verificar `uv --version` antes de ejecutar los comandos siguientes. El proyecto
exige uv 0.12.22; no sustituir el baseline por otra versión para resolver errores.

Desde la raíz del proyecto, en PowerShell:

```powershell
uv python install 3.13.16
uv sync --locked
uv run --locked src/blanquita_vision/main.py
```

Con el entorno ya preparado también se puede iniciar directamente:

```powershell
& ".venv\Scripts\python.exe" "src\blanquita_vision\main.py"
```

El proyecto utiliza src-layout y un proyecto virtual de uv; todavía no necesita
un backend de empaquetado ni un instalador .exe. La aplicación puede operar sin
Internet una vez instaladas las dependencias y el intérprete.

### Backend

```powershell
uv run --locked src/blanquita_vision/main.py --backend AUTO
```

También acepta un identificador de backend registrado por OpenCV, escrito sin
el prefijo `CAP_`, por ejemplo `DSHOW` si está disponible. La implementación
valida tanto el registro como la disponibilidad real mediante `hasBackend()`;
estar registrado no garantiza que el backend pueda cargarse. Un backend explícito
no disponible produce un error claro y no se sustituye silenciosamente.
Los códigos numéricos de OpenCV permanecen en el adapter.

No se impone resolución ni FPS al conectar. Los valores ausentes o no fiables
se muestran como «No disponible». El FPS medido corresponde a frames publicados
por unidad de tiempo de la sesión e incluye sus interrupciones de recuperación;
no equivale al FPS declarado por el driver ni a un objetivo de rendimiento.

### Lockfile y requirements

`pyproject.toml` + `uv.lock` son la fuente de verdad. `requirements.txt` es una
exportación derivada, con hashes y el grupo dev predeterminado (pytest).
Regenerarlo tras cualquier modificación aprobada del lockfile:

```powershell
uv export --locked --format requirements-txt --no-emit-project --output-file requirements.txt
```

No editar requirements manualmente ni instalar otra variante OpenCV en `.venv`.

## Uso de LIVE

1. Pulsar **Actualizar cámaras**.
2. Seleccionar **Cámara N**. La selección no abre el dispositivo.
3. Pulsar **Conectar**.
4. Observar video, estado y propiedades de captura.
5. **Capturar frame** obtiene una copia en memoria, sin crear archivos.
6. **Desconectar** libera la sesión; no inicia recuperación automática.

Para actualizar o cambiar de cámara, detener primero la sesión activa.

## Uso de SPEC-01 — Percepción del gancho celeste

### 1. Configurar e iniciar DETECCIÓN

Conectar la cámara en LIVE y abrir DETECCIÓN. Introducir explícitamente:

- H mínimo/máximo: escala OpenCV 0–179.
- S y V mínimo/máximo: 0–255.
- Área mínima del contorno en píxeles²; máxima opcional.
- Calidad mínima entre 0 y 1.
- Alpha EMA: `0 < alpha <= 1`.
- Si se activa morfología: kernel entero positivo impar, no mayor que las dimensiones
  del frame; se aplican apertura y cierre.

Los campos comienzan vacíos: no hay un rango celeste, área, calidad ni alpha
operativos inventados para el gancho real. Ajustarlos con la cámara, fondo e
iluminación del montaje. Los parámetros utilizados por los tests son exclusivamente
datos sintéticos y no constituyen un preset del producto.

Pulsar **Aplicar parámetros** y **Iniciar detector**. Sin calibración, se detecta y
sigue el objeto en píxeles; las coordenadas físicas permanecen no disponibles.
**Detener detector** libera el seguimiento y deja la cámara abierta.

### 2. Crear una calibración en memoria

1. Abrir CALIBRACIÓN y pulsar **Obtener frame de referencia**.
2. Elegir cuatro puntos distintos del plano de trabajo cuyas coordenadas físicas
   sean conocidas. No utilizar tres puntos colineales.
3. Seleccionar P1–P4 en la tabla y hacer clic en cada punto de la imagen congelada.
   Los clics se convierten a píxeles del frame original, no de la ventana escalada.
4. Introducir X/Y físicos de cada correspondencia y una unidad común declarada.
   El origen y sentidos positivos proceden de esas coordenadas, no de supuestos.
5. Pulsar **Calcular**, **Validar** y **Aplicar**.

La homografía se calcula fuera del hilo UI. El error interno se expresa en la
unidad declarada, pero no demuestra precisión real: cuatro pares pueden ajustarse
con error interno casi nulo. Validar otros puntos independientes.

La calibración se conserva solo en memoria. Cambiar cámara o resolución la invalida;
reconectar la misma identidad por índice con resolución equivalente no la invalida
por sí solo. Si la cámara o referencias se mueven físicamente, pulsar **Invalidar**
o **Recalibrar**. El índice no certifica por sí solo la identidad física de un
dispositivo que haya sido reemplazado.

### 3. Observar posición y seguimiento

LIVE presenta el frame realmente procesado con caja, punto visual y calidad.
DETECCIÓN muestra centroide, tracking, X/Y raw y filtered, timestamps, FPS y tiempos
de preprocessing, detección, tracking, estimación, EMA y pipeline completo.
La posición usa el centro de la caja validada; el centroide del contorno se muestra
como geometría independiente.

**Score de calidad:** solidez del contorno (`área / área del convex hull`) multiplicada
por ocupación de la máscara celeste dentro de su caja. Es un score geométrico/color,
no una probabilidad de que el objeto sea el gancho. Un empate entre los candidatos
principales se presenta como búsqueda ambigua, sin posición válida.

El detector verifica cada frame procesado. CSRT se mantiene cuando su caja es válida
y tiene intersección positiva con la detección actual. La pérdida o deriva reinicia
el tracker a partir de la detección actual y reinicia EMA. Cuando no existe una
detección inequívoca, se retiran overlays y posiciones anteriores como actuales.

Cambiar parámetros o calibración descarta observaciones pendientes y reinicia
tracker/EMA. Desconectar la cámara detiene la visión; iniciar después es manual.
Al cerrar, se espera también la finalización de Vision Worker y del cálculo de
calibración, manteniendo la política de cierre asíncrono.

### 4. Medir precisión con referencias independientes

Con calibración aplicada y visión activa, colocar el gancho en puntos físicos
conocidos que no se utilizaron para calcular la homografía. En CALIBRACIÓN,
introducir **X real / Y real** y pulsar **Medir error actual**.

Se muestran N, MAE X/Y, error 2D medio y máximo para posiciones raw y filtered.
Los agregados tienen memoria constante y no se guardan en archivos o SQLite.
Registrar los resultados de la prueba física; **Reiniciar mediciones** limpia los
agregados. Cambiar o invalidar la calibración también los reinicia.

Para validar rendimiento, usar las métricas de DETECCIÓN con la cámara y gancho
reales, documentando configuración, iluminación, resolución y duración observada.
Los objetivos de precisión, FPS y latencia permanecen TBD hasta medirlos.

### Alcance de test y validación de SPEC-01

| Casos | Comprobación automatizada |
|---|---|
| TC-01-001 a 003 | Inicio manual, precondiciones, detención sin cerrar cámara |
| TC-01-004 a 009 | Fixtures de color, distractores, ambigüedad, HSV y score |
| TC-01-010 a 012 | CSRT real sobre imágenes sintéticas, pérdida, deriva y reacquisición |
| TC-01-013 a 022 | Homografía conocida, degeneración, X/Y, Z=null e invalidación |
| TC-01-023 a 026 | EMA, valores inválidos, raw preservado y reinicio |
| TC-01-027 a 030 | Backpressure, errores, observación interna y arquitectura |

También se prueban clics sobre imagen escalada, cancelación de resultados tardíos,
cierre con visión/cálculo bloqueados y mediciones de error con referencias
sintéticas. Esto valida software, no precisión física del robot.

**Pendientes de hardware:** TC-01-031 a 036: gancho real, tuning HSV/calidad/EMA,
tracking real, cuatro correspondencias físicas, puntos independientes, benchmark
de precisión/rendimiento e invalidación después de mover físicamente la cámara.

La excepción USB de SPEC-00 con DSHOW se hereda: una lectura repetida de la última
imagen puede seguir siendo aceptada por el driver. SPEC-01 no corrige esa detección
física ni convierte timestamps de lectura en prueba de imagen nueva. Usar el
procedimiento manual aceptado y recalibrar si cambió la geometría.

La salida es `VisionObservation` interna. Protocolo, Mobile, persistencia y
VisionReport de red se implementan en SPEC-02; ONNX sigue en SPEC-03.

**Verificación de esta implementación:** suite completa ejecutada el 6 de octubre
de 2026 con `.venv\Scripts\python.exe -m pytest -q`: **104 passed, 1 skipped**.
Incluye las regresiones de SPEC-00 y software de SPEC-01. La omisión es el test
opcional de cámara física de SPEC-00. El resultado acredita **VALIDACIÓN EN SOFTWARE**;
los casos físicos de SPEC-01 siguen pendientes. No hubo cambios de dependencias.

## Uso de SPEC-02 — Red, persistencia y observabilidad

### Arranque y rutas

```powershell
& ".venv\Scripts\python.exe" "src\blanquita_vision\main.py" --backend DSHOW
```

El servidor inicia automáticamente en IPv4 `0.0.0.0:8765`, path `/vision`.
El cliente usa **`ws://IP_LAPTOP:8765/vision`**, no la dirección de bind `0.0.0.0`.
Por defecto se crea `data/blanquita_vision.db`; las capturas se guardan en
`data/captures/`. Elegir otra raíz al arrancar:

```powershell
& ".venv\Scripts\python.exe" "src\blanquita_vision\main.py" --backend DSHOW --data-dir "C:\Datos BLANQUITA"
```

Si el puerto está ocupado, se informa en DIAGNÓSTICOS y la visión local puede
seguir funcionando. No se cambia de puerto silenciosamente.

### Contrato Laptop ↔ Mobile

Todos los mensajes requieren `protocol`, `version`, `type`, `messageId`,
`timestamp` y `payload`. UUID válido, versión entera 1, JSON estricto sin campos
adicionales, valores finitos y timestamps con zona horaria. La serialización es
UTC ISO-8601 con sufijo Z. La presentación de tablas/diagnósticos usa hora local;
el detalle estructurado y exportaciones conservan UTC.

Al conectar, Mobile recibe hello, ready, vision.status, camera.status y
calibration.status. La conexión no abre la cámara ni inicia el detector.

Comandos aceptados:

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.start",
  "messageId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-10-06T15:30:00.123Z",
  "payload": {}
}
```

Para detener o consultar health, usar `vision.stop` o `vision.ping` con UUID y
timestamp actuales. Stop no desconecta la cámara. Start/stop repetidos son
idempotentes; start durante STOPPING responde como ocupado. Los comandos utilizan
el controlador de SPEC-01, sin canal al ESP32.

El heartbeat de aplicación se emite cada **2 s**; ping obtiene un heartbeat
correlacionado mediante `replyToMessageId`. No se introduce vision.pong.
El cliente Mobile debe declarar stale tras **6 s** sin heartbeat válido. El cliente
real debe implementar esa comprobación; los tests de loopback no la certifican.

`ready` significa cámara STREAMING con frame y parámetros/alpha aplicados, y
visión no ERROR/STOPPING. No implica posición física validada ni movimiento autorizado.
Solo se admite un cliente activo; se rechaza el segundo sin desplazar al primero.

Reportes: filtered X/Y en **mm**, Z y angle null, calidad 0–1, estado de calibración,
tracking, secuencia y timestamp original de observación. Sin detección/calibración
válida, posición física null. mm/cm/m se convierten con factores exactos; otras
unidades se rechazan. Los nuevos puntos de calibración en UI se declaran en mm.

Ante red lenta se conserva solo el reporte pendiente más reciente, además del
que ya está en envío. Solo un envío completado se registra como emitido; completar
send no demuestra que Mobile haya procesado el mensaje. Duración de envío no es RTT.

**LAN V1:** ws:// sin TLS ni autenticación, únicamente en red privada; no configurar
port-forwarding ni exponer directamente a Internet. Mobile no define rutas de
archivos ni puede enviar comandos físicos por este canal.

### SQLite, calibraciones y capturas

SQLite usa schema versionado, WAL cuando esté soportado, foreign keys y transacciones.
La conexión pertenece a Storage Worker. Se conservan sesiones, detecciones por
observación recibida, reportes realmente enviados, calibraciones y cuatro puntos,
eventos, errores, métricas y configuración. No hay eliminación automática.

Las sesiones empiezan al llegar realmente a RUNNING, conservan origen local_ui/mobile
y finalizan con timestamp/motivo. Los reinicios internos conservan el origen.
Las métricas se agregan en ventanas de un segundo; al cerrar puede guardarse una
ventana parcial. Los tiempos/FPS promediados proceden de las observaciones recibidas
por Application; los conteos usan diferencias de contadores, no sumas repetidas.

Aplicar una calibración la guarda automáticamente en mm. Al conectar una cámara
con resolución conocida se carga el perfil válido más reciente compatible. Esto
no certifica identidad física por índice ni que la cámara no se haya movido.
Invalidar/recalibrar se persiste; un resultado de carga tardío no revierte una
invalidación manual. Verificar geometría y recalibrar cuando corresponda.

En la aplicación completa, **Capturar frame** guarda JPG/PNG fuera del hilo UI y
añade metadata SQLite. Se asocia detección/posición solo cuando corresponde al
mismo frame y timestamp. No se crean imágenes por detección ni se usan BLOB grandes.
Si falla metadata después de escribir la imagen, el archivo se conserva y se
informa el fallo; no se declara captura completamente exitosa.

### Pantallas

- **ANALÍTICA:** tiempo real de los últimos 120 s e histórico por sesión/rango.
  Las series históricas muestran la página consultada, de 50 filas.
- **REPORTES:** categorías, filtro por sesión/texto/fechas, paginación y detalle.
  El detalle de calibración incluye los cuatro puntos; las capturas existentes se
  abren mediante el sistema y las faltantes producen un error controlado.
- **Exportaciones:** JSON/CSV de todas las filas filtradas, fuera de UI. JSON
  conserva null; CSV usa campo vacío. Columnas de exportación estables en inglés,
  timestamps UTC y coordenadas mm.
- **DIAGNÓSTICOS:** CAMERA, VISION, NETWORK, DATABASE, FILESYSTEM y SYSTEM.
  Muestra estado real, RX/TX, WAL, schema, cola y errores. CPU/RAM/GPU detallados
  aparecen como No disponible. La writability mostrada es la información de
  permisos disponible; guardar una captura verifica la escritura real.
- **AJUSTES:** formato/ruta de las siguientes capturas y nivel de logs. La ruta
  de DB se muestra; --data-dir se selecciona al arrancar. Endpoint permanece fijo.

### Límites y fallos

- Storage: máximo 256 trabajos pendientes; ordinarios hasta 192, reservando 64
  plazas a críticos. Como máximo dos capturas pendientes. Saturación se informa
  con estado/contadores; registros no aceptados o fallidos no se declaran persistidos.
- SQLite locked: espera de 0,1 s y hasta tres intentos separados por 0,2 s.
- WebSocket: 64 KiB por mensaje, timeout de envío 3 s, cierre de cliente 2 s.
  JSON/payload inválido no ejecuta acciones; incompatibilidad de protocolo/versión
  o binario cierra conexión.
- Ausencia de Mobile o storage degradado no detiene por sí sola la percepción.
- Cierre: bloquea acciones nuevas, cierra red, termina sesión y drena storage.
  Tras cinco segundos con operaciones activas mantiene la ventana con diagnóstico;
  no termina forzosamente hilos.

### Verificación y benchmarks

Última suite completa: **161 passed, 1 skipped**. Verifica contrato/Pydantic,
WebSocket loopback, heartbeat, cliente único, comandos idempotentes, latest-only,
SQLite, archivos reales JPG/PNG, exportaciones, UI, saturación, DB locked/unavailable,
fallo de metadata y cancelación de cargas tardías, además de regresiones previas.
La omisión sigue siendo la prueba opcional de cámara física de SPEC-00.

Benchmarks reproducibles con datos sintéticos (los números de ejemplo son parámetros
de ejecución, no objetivos aprobados):

```powershell
& ".venv\Scripts\python.exe" "tests\benchmark_network.py" --reports 1000 --client-delay 0.01
& ".venv\Scripts\python.exe" "tests\benchmark_storage.py" --rows 1000 --data-dir "C:\Datos BLANQUITA\benchmarks"
```

El benchmark SQLite usa **benchmark_storage.db**, separado de la BD operativa, y
conserva sus registros. El de red usa puerto efímero loopback y un cliente Python,
no un Mobile real. Solo se verificó su ejecución breve con datos sintéticos;
latencias/FPS y crecimiento en operación real siguen pendientes de medición.

**VALIDADO EN SOFTWARE.** Pendientes TC-02-058 a 060: LAN/Wi-Fi sin Internet,
interoperabilidad con Mobile real y detección de stale. Mobile debe alinear sus
modelos/UI con X/Y, Z=null, mm y UTC de SPEC-02; el documento móvil antiguo mostraba X/Z.
La validación física de SPEC-01 y la limitación USB aceptada de SPEC-00 no cambian.

### Fallos y cierre

- Primer frame inválido: ERROR, con posibilidad de reintento manual.
- Tres lecturas inválidas consecutivas durante streaming: RECOVERING.
- Recuperación: hasta tres intentos separados por dos segundos.
- Recuperación agotada: ERROR + Reintentar.
- Desconectar o cerrar cancela también descubrimiento, apertura y recuperación.
- Al perder la cámara se retira el video vigente; no se presenta un frame antiguo
  como video actual.
- Al cerrar, la aplicación espera asíncronamente hasta cinco segundos. Si una
  llamada nativa del driver continúa bloqueada, informa el error y mantiene la
  ventana abierta. No termina forzosamente el hilo. El cierre continúa cuando
  el worker logra finalizar.

Estos límites son decisiones iniciales aprobadas, pendientes de validación física.
Las llamadas nativas de VideoCapture no ofrecen cancelación portable garantizada:
la señal de cancelación se observa entre operaciones, no interrumpe el driver.

## Arquitectura

```text
Presentation (Qt Widgets, PyQtGraph, puente Qt)
    ↓
Application (cámara, VisionPipeline, CalibrationService, EMA)
    ↓
Domain (modelos y Ports de cámara, detector, tracker, calibración y posición)
    ↑
Adapters (OpenCvCamera, OpenCvHookDetector, CSRT, homografía, repositorio en memoria)
```

`CameraSession` ejecuta operaciones bloqueantes en un worker propietario.
`QtCameraRunner` entrega cambios mediante señales al controlador en el hilo de UI.
La UI no llama VideoCapture. Los frames tienen timestamp con zona horaria y
memoria propia de solo lectura en OpenCvCamera; snapshots poseen una copia independiente.

`tests/fixtures/fake_camera.py` sustituye CameraPort en pruebas y simula
descubrimiento, aperturas, lecturas inválidas, pérdidas y recuperación.

## Pruebas

```powershell
uv run --locked python -m pytest -q
```

Alternativa con el entorno preparado:

```powershell
& ".venv\Scripts\python.exe" -m pytest -q
```

Las pruebas Qt usan el plugin offscreen y PySide6.QtTest, sin pytest-qt ni nuevas
herramientas de calidad. Los límites temporales de los fakes son datos de prueba;
no modifican la política del producto.

### Trazabilidad de software

| Casos SPEC | Pruebas |
|---|---|
| TC-00-001, 002 | Arranque, ventana maximizada y navegación |
| TC-00-003, 004, 005 | Descubrimiento, empty state y selección sin apertura |
| TC-00-006 a 009 | Apertura, fallo, negociación y propiedades |
| TC-00-010, 011 | Latest-frame, coalescencia, frames inválidos |
| TC-00-012 a 016 | Pérdida, recuperación, agotamiento, retry y stop |
| TC-00-017, 018 | Snapshot coherente sin persistencia y ausencia de frame |
| TC-00-019 | Shutdown y liberación de worker |
| TC-00-020 | Sustitución por FakeCamera y separación de capas |

Se añaden casos de cancelación durante descubrimiento/apertura/recuperación,
driver bloqueado, responsividad UI, conversión BGR→RGB y consistencia del baseline.

### Pruebas con hardware

La suite normal no accede a cámaras reales. La prueba automatizada opcional de
apertura/lectura/cierre, que complementa TC-00-021, se ejecuta indicando un índice:

```powershell
uv run --locked python -m pytest -q -m hardware --hardware-camera-index 0
```

El usuario confirmó reconocimiento/conexión de la cámara, todos los botones del
frontend, desconexión/conexión manual y cierre de ventana con video activo seguido
de reapertura y conexión satisfactorias, completando el flujo manual TC-00-021.
En TC-00-022 confirmó que retirar el USB todavía no activa correctamente la
recuperación automática y aceptó recuperar manualmente; véase INC-00-001.
La compatibilidad física en Windows 10 y Windows 11 por separado no se ha registrado.

Para TC-00-023, elegir explícitamente índice y duración del benchmark:

```powershell
uv run --locked tests/benchmark_capture.py --camera-index 0 --seconds 60
```

El benchmark muestra LIVE y entrega JSON por consola con FPS, frames inválidos,
reemplazos, uso aproximado de CPU del proceso y tiempos de entrega a la UI.
El tiempo frame→render mide desde el retorno de la lectura hasta la llamada de
renderizado, no la latencia física de cámara/pantalla. Los intervalos de entrega
a la UI también dependen de la cámara; observar responsividad manualmente.
El valor de 60 segundos es un ejemplo de ejecución, no un umbral de aceptación.
No fija objetivos de rendimiento ni guarda capturas.

Los tests con FakeCamera solo acreditan **VALIDACIÓN EN SOFTWARE**.
Las pruebas con cámara física se registran por separado; la incidencia de
desconexión física y el benchmark requieren sus propias comprobaciones.

### Resultado de la verificación de implementación

Verificación ejecutada el 6 de octubre de 2026, usando Python 3.13.16 y
uv 0.12.22 con las dependencias exactas del baseline:

- `uv lock --check`: correcto.
- `uv run --locked python -m pytest -q`: **41 passed, 1 skipped**.
- Arranque/cierre del punto de entrada y benchmark comprobados con UI offscreen
  y FakeCamera; esa comprobación del benchmark no constituye una medición física.
- La prueba de cámara real se omite por defecto al no indicar un índice.
- En esta ejecución automatizada no se validaron físicamente TC-00-021,
  TC-00-022 ni TC-00-023. La confirmación posterior del usuario se registra abajo.
- Compatibilidad física en ambas versiones de Windows y objetivos numéricos de
  rendimiento: pendientes de las pruebas correspondientes.

### Validación manual confirmada por el usuario

**Fecha de registro:** 6 de octubre de 2026.  
**Responsable de la prueba:** usuario operador.  
**Evidencia:** confirmación del usuario en la conversación de que conectó la
cámara, el programa la reconoce y funciona correctamente, y revisó el frontend
con resultado satisfactorio. En un reporte posterior confirmó todos los botones,
incluidos Conectar y Desconectar, y señaló un fallo al retirar físicamente el USB.

| Comprobación | Resultado | Alcance |
|---|---|---|
| Reconocimiento y conexión de cámara física | Confirmado por el usuario | Comprobación funcional de hardware; aporta evidencia parcial para TC-00-021 |
| Funcionamiento del frontend | Confirmado por el usuario | Revisión visual y funcional general de la interfaz en ejecución real |
| Todos los botones, incluidos Conectar y Desconectar | Confirmado por el usuario | Prueba funcional manual con cámara real |
| Escenarios automatizados de software | 44 passed, 1 skipped en la última ejecución previa | Pruebas con fakes, integración Qt, arquitectura y entorno |
| Desconexión y conexión manual | Confirmado por el usuario | TC-00-021: desconexión desde el botón y reapertura funcional |
| Cierre de ventana y posterior reutilización de cámara | Confirmado explícitamente por el usuario | TC-00-021: cierre con video activo, reapertura y conexión satisfactorias |
| Retirada física USB y recuperación | Fallido; limitación conocida aceptada para el cierre | TC-00-022 / INC-00-001 / DEC-00-014 |
| Benchmark de captura real | No ejecutado, confirmado por el usuario | TC-00-023: mediciones pendientes como seguimiento |
| Compatibilidad física en Windows 10 y Windows 11 | Pendiente de registro en ambas plataformas | No se identifica la versión de Windows de la prueba manual reportada |

La confirmación corresponde al reconocimiento de la **cámara**, propio de SPEC-00.
La detección del gancho continúa perteneciendo a SPEC-01.

**Estado de validación:** VALIDADO EN SOFTWARE para los escenarios automatizados
y VALIDADO EN HARDWARE para el flujo funcional manual confirmado por el usuario,
con excepción aceptada para recuperación automática de retirada USB.
La SPEC queda en **VALIDATED** por solicitud y aceptación expresas del usuario;
no se acredita recuperación USB automática satisfactoria ni benchmark ejecutado.

### INC-00-001 — Pérdida USB no detectada durante captura

**Estado:** LIMITACIÓN CONOCIDA ACEPTADA PARA EL CIERRE DE SPEC-00. Backend DSHOW confirmado; la recuperación automática de retirada USB sigue sin corregirse.

**Reporte del usuario:** con la cámara conectada en el programa, retirar el USB
no produce automáticamente un cambio de estado. Volver a insertar el USB tampoco
recupera automáticamente la captura. Los botones Conectar y Desconectar funcionan.

**Detalles adicionales confirmados:** backend efectivo **DSHOW**; al retirar el
USB, el contador Frames y Último frame continúan actualizándose muy lentamente,
mientras la imagen permanece congelada en la última captura anterior a la retirada.

**Comportamiento esperado:** tras tres lecturas inválidas consecutivas, pasar a
RECOVERING, retirar el video vigente y ejecutar hasta tres intentos separados por
dos segundos. Si la cámara vuelve durante los intentos y entrega frames válidos,
volver a STREAMING. Si se agotan, pasar a ERROR y requerir Reintentar; no se espera
una reconexión automática indefinida después de agotar la política.

**Revisión técnica:** el ciclo actual solo detecta pérdida cuando `CameraPort.read()`
retorna un frame inválido. La progresión de Frames demuestra que siguen publicándose
lecturas aceptadas como válidas, aunque el usuario observa la última imagen estática.
El timestamp se asigna al retornar la lectura; no acredita que el dispositivo haya
capturado una imagen nueva. Este comportamiento es consistente con entrega repetida
de la última imagen mediante DSHOW. No corresponde a un bloqueo permanente de toda
la lectura, aunque pueda haber esperas largas entre retornos.

La implementación no dispone de detección independiente de presencia física USB
ni de frescura certificada por el driver. No se debe interpretar una imagen estática
como prueba de desconexión, porque también puede corresponder a una escena inmóvil.

**Resultado de la comparación con MSMF:** el usuario ejecutó la aplicación con
`--backend MSMF` y al actualizar cámaras no obtuvo dispositivos. La línea de
backend mostraba «MSMF / efectivo: No disponible». La comprobación del entorno
confirmó que MSMF está registrado en OpenCV pero `hasBackend(MSMF)` devuelve False,
mientras DSHOW está registrado y `hasBackend(DSHOW)` devuelve True.

«Efectivo: No disponible» indica que no existe una sesión abierta de la cual leer
el backend efectivo; ese texto por sí solo no prueba ausencia física de cámaras.
La validación de backends se corrigió según INC-00-002, registrada abajo.

Para volver a la configuración con la que el usuario confirmó captura funcional,
cerrar la instancia anterior, conectar el USB e iniciar con DSHOW explícito:

```powershell
& ".venv\Scripts\python.exe" "src\blanquita_vision\main.py" --backend DSHOW
```

Después, actualizar cámaras, seleccionar y conectar. La indisponibilidad de MSMF
impide comparar la recuperación USB con ese backend en el entorno actual.
El usuario confirmó que, al volver a DSHOW, el programa reconoce nuevamente la cámara
y funciona correctamente; reportó después un texto desactualizado en la barra
inferior, corregido en INC-00-003.
La detección de pérdida USB con DSHOW sigue pendiente de corrección; no se
considera resuelta por recuperar la selección de backend. Al solicitar el cierre,
el usuario confirmó que el fallo persiste y aceptó expresamente el procedimiento
manual, sin dedicar más tiempo a corregirlo en esta SPEC.

**Verificación de software realizada al revisar el reporte:** cinco pruebas
existentes de recuperación, agotamiento, cancelación durante recuperación y
operaciones bloqueadas: **5 passed, 12 deselected**. Utilizan fakes; las operaciones
bloqueadas cubiertas son descubrimiento/apertura, no una lectura real bloqueada
durante streaming. Este resultado no reproduce ni resuelve la incidencia física.

**Procedimiento manual aceptado:**

1. Pulsar **Desconectar** en la interfaz.
2. Reconectar físicamente la cámara al USB.
3. Pulsar **Conectar** en la interfaz.

La limitación se acepta como excepción de cierre **DEC-00-014**. TC-00-022 permanece
fallido y no se declara corregida la recuperación automática. La comprobación
física fue realizada por el usuario; el agente revisó código y pruebas de software.

### INC-00-002 — Backend registrado pero no disponible

**Estado:** validación de backend corregida y comprobada en software.

**Causa comprobada:** `backend_id()` solo verificaba si el identificador aparecía
en `getBackends()`. MSMF aparece en ese registro, pero no está disponible para
cargarse en el entorno comprobado. La causa de esa indisponibilidad interna no
se ha determinado y no se atribuye al dispositivo de cámara.

**Corrección:** comprobar además `cv2.videoio_registry.hasBackend()`. Si el backend
no está disponible, informar `backend_unavailable` con su nombre antes de probar
índices o abrir la cámara. No introducir fallback ni cambiar AUTO como default.
En el arranque con un backend explícito no disponible, el mensaje se presenta en
consola y la aplicación no inicia con una configuración inválida.

**Verificación posterior a la corrección:**

- Pruebas de descubrimiento/apertura con backend registrado pero no disponible.
- Prueba de conservación de un backend explícito disponible.
- Suite completa: **44 passed, 1 skipped**, ejecutada mediante
  `.venv\Scripts\python.exe -m pytest -q`.
- La prueba omitida sigue requiriendo cámara real e índice explícito.

La comprobación del registro de OpenCV no abre dispositivos ni acredita una
validación física nueva. El usuario confirmó posteriormente el funcionamiento
con DSHOW. INC-00-001 se conserva como limitación conocida aceptada para el cierre.

### INC-00-003 — Barra inferior muestra cámara desconectada durante captura

**Estado:** CERRADA; corregida y validada en software, con confirmación manual final del usuario.

**Reporte del usuario:** la cámara funciona después de volver a DSHOW, pero la barra
inferior conserva «Percepción local · Cámara desconectada» durante captura.

**Causa:** el mensaje estaba fijado durante la construcción de MainWindow y no
estaba suscrito a los cambios de estado de CameraController.

**Corrección:** sincronizar la barra inferior con CameraRuntimeState. Durante
STREAMING muestra «Percepción local · Cámara conectada · Video en vivo»; también
refleja descubrimiento, conexión, recuperación, error, detención y desconexión.
El mensaje permanece visible al navegar a otros módulos. Los mensajes de cierre
y timeout conservan su prioridad y se retira la suscripción al cerrar la ventana.

**Verificación:** se ampliaron las pruebas de integración existentes para comprobar
el texto inicial, conexión, navegación con cámara activa, desconexión, error y
recuperación. Los casos de cierre con driver bloqueado siguen pasando. Suite
completa ejecutada con `.venv\Scripts\python.exe -m pytest -q`:
**44 passed, 1 skipped**. El usuario confirmó después que el programa funciona
correctamente y solicitó terminar y validar SPEC-00. Esa comprobación manual
del frontend no modifica la detección de pérdida USB de INC-00-001.

## Cierre de SPEC-00

**Fecha de registro:** 6 de octubre de 2026.  
**Estado:** VALIDATED — terminada y validada en el alcance aceptado por el usuario.

El cierre fue solicitado expresamente por el usuario, quien confirmó funcionamiento
de cámara y frontend, todos los botones y cierre/reapertura con video activo.
La última suite automatizada registrada terminó con **44 passed, 1 skipped**.

### Excepción aceptada y seguimiento

- **DEC-00-014 / INC-00-001:** la retirada física USB con DSHOW todavía falla.
  El usuario acepta recuperar mediante Desconectar → reconectar USB → Conectar
  y solicita no dedicar más tiempo a corregir esta condición en SPEC-00.
  La prueba TC-00-022 permanece fallida; no se presenta como recuperación automática
  validada ni se oculta la desviación de los criterios relacionados.
- **TC-00-023:** el usuario confirmó que no ejecutó el benchmark. Las mediciones
  y objetivos numéricos siguen pendientes/TBD como seguimiento, sin datos inventados.
- **Windows 10/Windows 11:** no se registra validación física por separado en
  ambas plataformas; la confirmación corresponde al entorno utilizado por el usuario.

El estado VALIDATED refleja este cierre aceptado con limitación conocida, no una
afirmación de ausencia de fallos o de mediciones completadas. La evidencia física
procede del usuario; esta actualización documental no representa pruebas nuevas
realizadas por el agente. No se inicia automáticamente la SPEC siguiente.
