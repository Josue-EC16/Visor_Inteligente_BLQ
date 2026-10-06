# SPEC-00 — Fundación, arquitectura, UI y captura

## 1. Identificación

| Campo | Valor |
|---|---|
| SPEC ID | SPEC-00 |
| Nombre | Fundación, arquitectura, UI y captura |
| Archivo oficial | `SPEC-00_FOUNDATION_ARCHITECTURE_UI_CAPTURE.md` |
| Versión | 1.0.0 |
| Estado | VALIDATED |
| Proyecto | BLANQUITA Vision |
| Plataforma objetivo | Windows 10 / Windows 11 x64 |
| Fecha | 2026-10-06 |
| Dependencias previas | Ninguna SPEC anterior |
| Specs relacionadas | SPEC-01, SPEC-02, SPEC-03 |

### 1.1. Fuentes normativas

Esta SPEC debe interpretarse conjuntamente con:

1. `AGENTS.md`
2. `VISION_INTELIGENTE_BLQ.md`
3. `ARQUITECTURA_CONEXION.md`
4. `APP_MOVIL_BLANQ_V2.md`
5. Las decisiones explícitas aprobadas por el usuario para SPEC-00.

En caso de contradicción, el agente deberá aplicar la jerarquía documental definida en `AGENTS.md` y reportar cualquier incompatibilidad antes de alterar comportamiento.

---

## 2. Contexto

BLANQUITA Vision es la aplicación desktop de percepción visual del proyecto BLANQUITA.

La arquitectura global del sistema se divide en:

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

> La laptop percibe, el móvil decide y el ESP32 ejecuta y protege.

SPEC-00 construye la fundación técnica de BLANQUITA Vision y establece las bases que utilizarán todas las SPECS posteriores.

Esta SPEC cubre:

```text
entorno reproducible
+
estructura arquitectónica
+
shell de aplicación
+
navegación
+
tema visual
+
abstracción de cámara
+
descubrimiento/selección
+
captura
+
video en vivo
+
estado de cámara
+
concurrencia base
+
manejo de errores de captura
+
testabilidad
```

No incluye todavía procesamiento visual de alto nivel.

---

## 3. Objetivo

Construir y especificar la fundación de BLANQUITA Vision para que la aplicación pueda:

1. ejecutarse de forma reproducible en Windows;
2. iniciar una interfaz desktop basada en PySide6;
3. presentar la navegación completa de V1;
4. iniciar en la pantalla LIVE;
5. detectar y seleccionar cámaras compatibles con OpenCV;
6. conectar y desconectar manualmente una cámara;
7. capturar frames fuera del hilo principal de UI;
8. mostrar video en vivo;
9. mantener únicamente el frame más reciente cuando exista presión de procesamiento;
10. recuperar de forma controlada una desconexión de cámara;
11. exponer contratos desacoplados para las SPECS posteriores;
12. permanecer independiente del hardware específico de una webcam.

El resultado de SPEC-00 debe permitir que SPEC-01 añada calibración, detección y estimación de posición sin rediseñar la base de captura ni la estructura principal de la aplicación.

---

## 4. Alcance

### 4.1. IN SCOPE

SPEC-00 incluye:

- Python 3.13.16.
- `uv` 0.12.22.
- Entorno virtual local `.venv`.
- `pyproject.toml`.
- `uv.lock`.
- `requirements.txt` como export derivado para compatibilidad.
- PySide6 6.11.2.
- Qt Widgets.
- PyQtGraph 0.14.0.
- NumPy 2.5.3.
- `opencv-contrib-python-headless==4.14.0.94`.
- pytest 9.1.1 para pruebas asociadas.
- Arquitectura Hexagonal / Ports & Adapters.
- Estructura base del repositorio.
- Ventana principal.
- Inicio maximizado y ventana redimensionable.
- Tema principal negro, técnico y de alto contraste.
- Sidebar izquierdo.
- Navegación completa de V1.
- Pantallas placeholder para funcionalidades de SPECS futuras.
- Pantalla LIVE funcional.
- Detección lógica de dispositivos de captura compatibles.
- Representación de cámaras mediante índices de dispositivo.
- Actualización manual de la lista de cámaras.
- Selección de cámara.
- Apertura manual de cámara.
- Cierre manual de cámara.
- Backend de captura configurable.
- Backend inicial automático.
- Resolución inicial negociada por la cámara.
- FPS inicial negociado por la cámara.
- Lectura y presentación de resolución efectiva.
- Lectura y presentación de FPS efectivo cuando sea medible.
- Captura continua de frames.
- Estrategia `latest-frame`.
- Visualización en vivo.
- Obtención efímera de un frame puntual mediante acción de captura.
- Estados de cámara.
- Reconexión automática limitada ante pérdida de dispositivo.
- Botón de reintento cuando la recuperación automática se agota.
- Workers Qt.
- Señales/slots.
- Manejo de cierre ordenado.
- FakeCamera y componentes sustituibles para testing.
- Logs base de cámara/aplicación.
- Pruebas unitarias, integración, negativas y con hardware real cuando corresponda.

### 4.2. OUT OF SCOPE

SPEC-00 NO implementa:

- calibración;
- ArUco;
- chessboard;
- homografía;
- ROI de procesamiento;
- detección del gancho;
- tracking;
- `DetectorPort` productivo;
- `OpenCvHookDetector`;
- `OnnxHookDetector`;
- inferencia ONNX;
- estimación X/Y/Z;
- `PositionEstimate` funcional;
- validación geométrica;
- `VisionReport` productivo;
- WebSocket;
- protocolo Laptop ↔ Mobile;
- SQLite;
- almacenamiento persistente de capturas;
- reportes históricos;
- analítica histórica;
- Polars;
- diagnósticos completos;
- comunicación directa con ESP32;
- MQTT;
- grabación continua de video;
- multiprocessing;
- empaquetado final `.exe`.

La existencia de pantallas placeholder para estas funciones no implica implementación funcional.

---

## 5. Actores

### 5.1. Usuario operador

Persona que ejecuta BLANQUITA Vision y controla las operaciones locales del visor.

Responsabilidades en SPEC-00:

- iniciar la aplicación;
- navegar entre módulos;
- seleccionar cámara;
- actualizar lista de cámaras;
- conectar cámara;
- desconectar cámara;
- solicitar reintento;
- observar video;
- solicitar una captura puntual efímera.

### 5.2. BLANQUITA Vision

Sistema desktop responsable de coordinar UI, aplicación, dominio y adapters.

### 5.3. Cámara

Dispositivo de captura compatible con OpenCV/Windows.

### 5.4. OpenCV

Adapter tecnológico utilizado para descubrimiento lógico, apertura, configuración y lectura de frames.

### 5.5. Sistema operativo Windows

Proporciona acceso al hardware de captura y recursos de ejecución.

### 5.6. SPECS futuras

No son actores humanos, pero consumen contratos creados en SPEC-00:

- SPEC-01 consume frames y `CameraPort`.
- SPEC-02 consume eventos/capturas mediante contratos definidos.
- SPEC-03 reutiliza arquitectura, métricas y testabilidad.

---

## 6. Casos de uso

### UC-00-01 — Iniciar BLANQUITA Vision

**Actor:** Usuario operador.

**Precondiciones:**

- Python y dependencias instaladas en entorno de desarrollo, o runtime equivalente en una distribución futura.
- Configuración base válida.

**Trigger:** El usuario inicia la aplicación.

**Flujo principal:**

1. El sistema carga configuración base.
2. Inicializa infraestructura mínima.
3. Construye la ventana principal.
4. Aplica tema negro de alto contraste.
5. Construye el sidebar.
6. Registra todas las pantallas V1.
7. Abre `LIVE`.
8. La cámara permanece desconectada.
9. La interfaz queda disponible.

**Flujos alternativos:**

- Si una configuración opcional no existe, se utilizan valores seguros definidos por la aplicación.
- Si un componente no crítico falla, la UI debe iniciar mostrando el error correspondiente cuando sea posible.

**Postcondiciones:**

- Aplicación abierta.
- Pantalla LIVE visible.
- Cámara no activa hasta acción explícita del usuario.

**Errores:**

- configuración inválida;
- inicialización UI fallida;
- recurso gráfico no disponible.

---

### UC-00-02 — Navegar entre módulos

**Actor:** Usuario operador.

**Precondiciones:**

- Aplicación iniciada.

**Trigger:** Selección de un elemento del sidebar.

**Flujo principal:**

1. El usuario selecciona un módulo.
2. El shell cambia la pantalla central.
3. Si el módulo todavía pertenece a una SPEC futura, se muestra su placeholder.
4. El sidebar conserva el estado de navegación.

**Postcondiciones:**

- La pantalla seleccionada queda visible.

**Errores:**

- ruta/pantalla no registrada;
- error de construcción de pantalla.

---

### UC-00-03 — Actualizar lista de cámaras

**Actor:** Usuario operador.

**Precondiciones:**

- Aplicación iniciada.
- Pantalla LIVE disponible.

**Trigger:** Botón `Actualizar cámaras`.

**Flujo principal:**

1. El sistema inicia la enumeración lógica.
2. Prueba índices candidatos sin acoplar el dominio a un modelo físico.
3. Identifica índices que pueden abrirse de forma válida.
4. Cierra recursos temporales utilizados en la enumeración.
5. Presenta opciones como `Cámara 0`, `Cámara 1`, etc.
6. Conserva selección previa únicamente si continúa disponible.

**Flujos alternativos:**

- Si no se encuentra ninguna cámara, muestra empty state.
- Si un índice produce error, se descarta y se registra el evento sin bloquear la enumeración completa.

**Postcondiciones:**

- Lista de cámaras actualizada.

**Errores:**

- permisos;
- dispositivo ocupado;
- backend no disponible;
- error de apertura.

---

### UC-00-04 — Seleccionar cámara

**Actor:** Usuario operador.

**Precondiciones:**

- Existe al menos una cámara disponible.

**Trigger:** Usuario selecciona una cámara.

**Flujo principal:**

1. El usuario elige un índice.
2. El sistema actualiza la selección.
3. No abre todavía la cámara por la selección sola.

**Postcondiciones:**

- Una cámara queda seleccionada para futura conexión.

**Errores:**

- índice dejó de estar disponible.

---

### UC-00-05 — Conectar cámara manualmente

**Actor:** Usuario operador.

**Precondiciones:**

- Cámara seleccionada.
- No existe otra sesión de captura activa.

**Trigger:** Botón `Conectar` / `Iniciar cámara`.

**Flujo principal:**

1. El sistema transiciona a `CONNECTING`.
2. `CameraPort` solicita apertura al adapter.
3. El adapter usa backend configurado.
4. Si backend = automático, OpenCV negocia el backend.
5. La cámara utiliza inicialmente su resolución/FPS negociados.
6. Se consulta configuración efectiva.
7. Se inicia el worker de captura.
8. La cámara pasa a `STREAMING`.
9. LIVE comienza a recibir el frame más reciente.

**Flujos alternativos:**

- Si la cámara está ocupada, la apertura falla.
- Si el backend seleccionado no funciona, se informa el error.
- El sistema no debe cambiar silenciosamente de backend explícitamente seleccionado sin una política futura aprobada.

**Postcondiciones:**

- Video en vivo activo o estado `ERROR`.

**Errores:**

- cámara no disponible;
- cámara ocupada;
- backend inválido;
- apertura fallida;
- primer frame inválido.

---

### UC-00-06 — Visualizar video en vivo

**Actor:** Usuario operador.

**Precondiciones:**

- Cámara en `STREAMING`.

**Trigger:** Disponibilidad de nuevos frames.

**Flujo principal:**

1. Camera Worker obtiene un frame.
2. Valida que el frame no sea vacío.
3. Actualiza el slot `latest-frame`.
4. Si existía un frame no consumido, se reemplaza.
5. La UI recibe la notificación correspondiente.
6. PyQtGraph/Qt renderiza el frame actual.
7. Se actualiza información básica de captura cuando corresponda.

**Postcondiciones:**

- El usuario observa el frame más reciente disponible.

**Errores:**

- frame vacío;
- timeout;
- dispositivo perdido;
- conversión de formato fallida.

---

### UC-00-07 — Desconectar cámara manualmente

**Actor:** Usuario operador.

**Precondiciones:**

- Cámara abierta o en proceso de recuperación.

**Trigger:** Botón `Desconectar` / `Detener cámara`.

**Flujo principal:**

1. Se marca cancelación intencional.
2. Se detiene ciclo de captura.
3. Se liberan recursos de OpenCV.
4. Se limpia el frame activo de LIVE.
5. El estado vuelve a `DISCONNECTED`.

**Postcondiciones:**

- No quedan lecturas activas de cámara.

**Errores:**

- fallo al liberar recurso: se registra, pero el sistema debe continuar el cierre lógico.

---

### UC-00-08 — Recuperar cámara desconectada inesperadamente

**Actor:** Sistema.

**Precondiciones:**

- Cámara estaba en `STREAMING`.
- La desconexión no fue solicitada por el usuario.

**Trigger:** Lectura repetidamente inválida o pérdida detectada del dispositivo.

**Flujo principal:**

1. Sistema cambia a `RECOVERING`.
2. Detiene la sesión de captura defectuosa.
3. Libera recursos.
4. Ejecuta una política de reintento automática limitada.
5. Si la cámara vuelve a estar disponible, reabre el dispositivo.
6. Reinicia captura.
7. Vuelve a `STREAMING`.

**Flujo alternativo:**

1. Si se agota la política de recuperación:
2. Cambia a `ERROR`.
3. Mantiene la aplicación operativa.
4. Muestra botón `Reintentar`.
5. No continúa reintentando indefinidamente.

**Postcondiciones:**

- `STREAMING` si se recupera.
- `ERROR` si se agota la política.

---

### UC-00-09 — Reintentar manualmente conexión

**Actor:** Usuario operador.

**Precondiciones:**

- Estado `ERROR`.
- Existe cámara seleccionada.

**Trigger:** Botón `Reintentar`.

**Flujo principal:**

1. El sistema reinicia el intento de conexión.
2. Pasa a `CONNECTING`.
3. Si abre correctamente, pasa a `STREAMING`.
4. Si falla, vuelve a `ERROR`.

---

### UC-00-10 — Solicitar captura puntual efímera

**Actor:** Usuario operador.

**Precondiciones:**

- Existe un frame válido disponible.

**Trigger:** Botón `Capturar frame`.

**Flujo principal:**

1. El usuario solicita captura.
2. La aplicación obtiene una copia consistente del frame más reciente.
3. Genera un resultado efímero `CapturedFrame`.
4. Puede mostrarse feedback local de éxito.
5. El frame NO se guarda físicamente en SPEC-00.

**Postcondiciones:**

- Existe un frame puntual disponible en memoria para consumidores posteriores.

**Errores:**

- no existe frame válido;
- cámara desconectada.

---

### UC-00-11 — Cerrar aplicación con cámara activa

**Actor:** Usuario operador.

**Precondiciones:**

- Aplicación abierta.

**Trigger:** Cierre de ventana.

**Flujo principal:**

1. El shell inicia shutdown.
2. Cancela operaciones de captura.
3. Solicita detención del worker.
4. Libera cámara.
5. Desconecta señales necesarias.
6. Espera cierre ordenado dentro de la política definida.
7. Finaliza la aplicación.

**Postcondiciones:**

- Recursos liberados.
- Sin worker de captura huérfano.

---

## 7. Requisitos funcionales

### Fundación y entorno

**RF-00-001**  
El sistema deberá ejecutarse sobre Python 3.13.16 durante desarrollo.

**RF-00-002**  
El proyecto deberá utilizar `uv` 0.12.22 como herramienta principal para administrar intérprete, entorno virtual, dependencias y lockfile.

**RF-00-003**  
El proyecto deberá utilizar un entorno virtual local denominado `.venv`.

**RF-00-004**  
`.venv` no deberá considerarse artefacto fuente del proyecto ni fuente de verdad de dependencias.

**RF-00-005**  
`pyproject.toml` deberá declarar las dependencias directas aprobadas del proyecto.

**RF-00-006**  
`uv.lock` deberá bloquear el grafo reproducible de dependencias.

**RF-00-007**  
El proyecto deberá disponer de `requirements.txt` como artefacto de compatibilidad/exportación derivado de las dependencias bloqueadas.

**RF-00-008**  
`requirements.txt` no deberá convertirse en una segunda fuente de verdad independiente de `pyproject.toml` y `uv.lock`.

### Shell y navegación

**RF-00-009**  
El sistema deberá utilizar PySide6 6.11.2 con Qt Widgets como framework principal de UI.

**RF-00-010**  
El sistema deberá utilizar PyQtGraph 0.14.0 para visualización de video y componentes gráficos donde corresponda.

**RF-00-011**  
La aplicación deberá iniciar con la ventana principal maximizada.

**RF-00-012**  
La ventana principal deberá ser redimensionable.

**RF-00-013**  
La aplicación deberá iniciar mostrando la pantalla `LIVE`.

**RF-00-014**  
La cámara no deberá conectarse automáticamente al iniciar la aplicación.

**RF-00-015**  
La navegación principal deberá implementarse mediante un sidebar izquierdo.

**RF-00-016**  
El sidebar deberá mostrar desde SPEC-00 los módulos:

- LIVE
- CALIBRACIÓN
- DETECCIÓN
- ANALÍTICA
- REPORTES
- DIAGNÓSTICOS
- AJUSTES

**RF-00-017**  
Los módulos no implementados todavía deberán mostrar una pantalla placeholder sin ejecutar funcionalidad perteneciente a SPECS futuras.

**RF-00-018**  
La UI visible al usuario deberá estar en español.

### Cámara

**RF-00-019**  
El dominio deberá abstraer la captura mediante `CameraPort`.

**RF-00-020**  
La implementación inicial de `CameraPort` deberá ser `OpenCvCamera`.

**RF-00-021**  
La lógica de dominio no deberá depender de una marca, modelo, índice fijo, resolución fija o backend concreto de cámara.

**RF-00-022**  
El sistema deberá poder actualizar la lista de cámaras disponibles mediante una acción explícita del usuario.

**RF-00-023**  
Las cámaras descubiertas en SPEC-00 deberán representarse mediante identificadores basados en índice, por ejemplo `Cámara 0`.

**RF-00-024**  
La selección de una cámara no deberá abrir automáticamente el dispositivo.

**RF-00-025**  
El usuario deberá iniciar manualmente la conexión de cámara.

**RF-00-026**  
El usuario deberá poder detener manualmente la cámara.

**RF-00-027**  
El adapter OpenCV deberá utilizar `cv2.VideoCapture`.

**RF-00-028**  
El sistema deberá permitir configuración de backend de captura.

**RF-00-029**  
El backend inicial deberá ser automático.

**RF-00-030**  
La arquitectura deberá permitir soportar en el futuro backends específicos de Windows sin modificar el dominio.

**RF-00-031**  
En la primera conexión, la aplicación deberá respetar inicialmente la resolución negociada por la cámara.

**RF-00-032**  
En la primera conexión, la aplicación deberá respetar inicialmente el FPS negociado por la cámara.

**RF-00-033**  
La aplicación deberá leer y mostrar la resolución efectiva utilizada por la captura.

**RF-00-034**  
La aplicación deberá leer y mostrar el FPS efectivo/reportado cuando el backend pueda proporcionarlo.

### Captura y visualización

**RF-00-035**  
La captura continua no deberá ejecutarse en el hilo principal de UI.

**RF-00-036**  
La captura deberá ejecutarse mediante un worker Qt o mecanismo equivalente aprobado dentro del ecosistema PySide6.

**RF-00-037**  
Cada frame deberá validarse antes de publicarse como frame disponible.

**RF-00-038**  
El sistema deberá utilizar estrategia `latest-frame`.

**RF-00-039**  
Si llega un nuevo frame antes de que el anterior sea consumido, el sistema deberá reemplazar el frame pendiente y descartar el frame obsoleto.

**RF-00-040**  
La cola de frames pendientes no deberá crecer de forma no acotada.

**RF-00-041**  
La pantalla LIVE deberá mostrar el frame más reciente disponible.

**RF-00-042**  
La pantalla LIVE deberá mostrar estado de cámara.

**RF-00-043**  
La pantalla LIVE deberá mostrar cámara seleccionada.

**RF-00-044**  
La pantalla LIVE deberá mostrar resolución efectiva.

**RF-00-045**  
La pantalla LIVE deberá mostrar FPS efectivo/reportado cuando esté disponible.

### Recuperación

**RF-00-046**  
Una desconexión inesperada de cámara deberá cambiar el estado a `RECOVERING`.

**RF-00-047**  
El sistema deberá ejecutar una política automática y limitada de recuperación.

**RF-00-048**  
La recuperación automática no deberá reintentarse indefinidamente.

**RF-00-049**  
Si la recuperación se agota, el sistema deberá cambiar a `ERROR`.

**RF-00-050**  
En `ERROR`, la pantalla LIVE deberá ofrecer una acción `Reintentar`.

**RF-00-051**  
La pérdida de la cámara no deberá cerrar la aplicación.

### Captura puntual efímera

**RF-00-052**  
La pantalla LIVE deberá ofrecer una acción `Capturar frame` cuando exista un frame válido.

**RF-00-053**  
La acción de captura deberá obtener una copia consistente del frame más reciente.

**RF-00-054**  
SPEC-00 no deberá guardar esa captura en filesystem ni SQLite.

**RF-00-055**  
La arquitectura deberá permitir que SPEC-02 consuma posteriormente el resultado de captura sin modificar el contrato base de captura.

### Cierre

**RF-00-056**  
Al cerrar la aplicación, el sistema deberá cancelar la captura activa.

**RF-00-057**  
El sistema deberá liberar el recurso de cámara durante el shutdown.

**RF-00-058**  
El sistema deberá evitar dejar workers de captura activos después del cierre lógico de la aplicación.

---

## 8. Requisitos no funcionales

### Compatibilidad

**RNF-00-001**  
La aplicación deberá ser compatible con Windows 10 y Windows 11 de 64 bits.

**RNF-00-002**  
La captura deberá funcionar con cámaras accesibles mediante OpenCV en el sistema objetivo.

### Arquitectura

**RNF-00-003**  
La solución deberá respetar Arquitectura Hexagonal / Ports & Adapters.

**RNF-00-004**  
El dominio no deberá importar PySide6, `cv2`, `sqlite3`, `websockets` u `onnxruntime` cuando exista una abstracción mediante Ports.

**RNF-00-005**  
Presentation no deberá acceder directamente al hardware saltándose Application/Ports.

**RNF-00-006**  
La arquitectura deberá permitir sustituir `OpenCvCamera` por `FakeCamera`.

### Responsividad

**RNF-00-007**  
La captura continua no deberá bloquear el event loop principal de Qt.

**RNF-00-008**  
La navegación y los controles principales deberán permanecer interactivos durante la captura normal.

**RNF-00-009**  
Los objetivos numéricos de FPS, latencia y uso de CPU permanecerán `TBD — definir mediante benchmark`; no se establecerán valores arbitrarios en SPEC-00.

### Memoria y backpressure

**RNF-00-010**  
La política `latest-frame` deberá evitar acumulación no acotada de frames en memoria.

**RNF-00-011**  
Los frames descartados por obsolescencia deberán poder ser contabilizados mediante métrica cuando se implemente instrumentación suficiente.

### Confiabilidad

**RNF-00-012**  
Un frame inválido no deberá provocar cierre de la aplicación.

**RNF-00-013**  
Una cámara desconectada no deberá bloquear permanentemente la UI.

**RNF-00-014**  
La aplicación deberá liberar recursos de captura incluso ante cierre con streaming activo.

### Mantenibilidad

**RNF-00-015**  
El código nuevo deberá utilizar nombres de clases, métodos, variables y módulos en inglés.

**RNF-00-016**  
Los mensajes visibles al usuario deberán utilizar español.

**RNF-00-017**  
El código nuevo deberá utilizar type hints cuando mejoren claridad y mantenibilidad.

**RNF-00-018**  
No se introducirán Ruff, mypy, pyright ni nuevas herramientas de calidad no aprobadas.

### UI/UX

**RNF-00-019**  
La interfaz deberá utilizar un diseño principal negro, técnico y de alto contraste.

**RNF-00-020**  
El video deberá ser el elemento visual principal de LIVE cuando la cámara esté conectada.

**RNF-00-021**  
Los estados `DISCONNECTED`, `CONNECTING`, `STREAMING`, `RECOVERING` y `ERROR` deberán distinguirse claramente mediante texto y tratamiento visual.

**RNF-00-022**  
La ausencia de cámara deberá presentarse como estado normal gestionado y no como crash.

### Seguridad de responsabilidad

**RNF-00-023**  
BLANQUITA Vision no deberá controlar directamente al ESP32.

**RNF-00-024**  
SPEC-00 no deberá introducir canales de control físico.

---

## 9. Reglas de negocio / dominio

### BR-00-001 — Autoridad

BLANQUITA Vision es una fuente de percepción y nunca adquiere autoridad de movimiento físico.

### BR-00-002 — Apertura explícita

Seleccionar una cámara no equivale a conectarla.

### BR-00-003 — Inicio seguro

La aplicación inicia con la cámara desconectada.

### BR-00-004 — Frame válido

Un frame solo puede convertirse en `LatestFrame` si:

- la lectura fue reportada como exitosa;
- el objeto de imagen existe;
- la imagen no está vacía;
- sus dimensiones son válidas.

### BR-00-005 — Latest frame wins

Ante múltiples frames pendientes:

```text
frame_n antiguo
     ↓ llega frame_n+1
descartar frame_n pendiente
     ↓
conservar frame_n+1
```

El sistema prioriza actualidad sobre reproducción exhaustiva.

### BR-00-006 — No persistencia en SPEC-00

`CapturedFrame` es efímero.

No implica:

```text
archivo
SQLite
reporte persistido
```

### BR-00-007 — Recuperación acotada

Una desconexión inesperada habilita reintento automático limitado.

No se permite un loop infinito de reconexión.

### BR-00-008 — Desconexión intencional

Si el usuario solicita desconexión, el sistema no debe interpretar la detención como fallo ni iniciar recuperación automática.

### BR-00-009 — Configuración efectiva

La resolución/FPS mostrados deben representar los valores efectivos/reportados de la sesión, no valores asumidos.

### BR-00-010 — Backend

El backend pertenece al adapter y a configuración de infraestructura, no al dominio.

---

## 10. Modelo de estados

### 10.1. CameraState

Estados:

```text
DISCONNECTED
DISCOVERING
CONNECTING
STREAMING
RECOVERING
ERROR
STOPPING
```

### 10.2. Transiciones válidas

```text
DISCONNECTED
   │
   ├── refresh cameras ──────────> DISCOVERING
   │                                  │
   │                                  └────────> DISCONNECTED
   │
   └── connect ──────────────────> CONNECTING
                                      │
                           success ───┴─── failure
                              │              │
                              ▼              ▼
                          STREAMING        ERROR
                              │
               ┌──────────────┼──────────────┐
               │              │              │
       user stop        device lost       app close
               │              │              │
               ▼              ▼              ▼
           STOPPING      RECOVERING      STOPPING
               │              │
               ▼      ┌───────┴────────┐
        DISCONNECTED  │                │
                   recovered        exhausted
                      │                │
                      ▼                ▼
                  STREAMING          ERROR

ERROR
   │
   ├── retry ─────────────────────> CONNECTING
   └── refresh cameras ───────────> DISCOVERING
```

### 10.3. Transiciones inválidas

Ejemplos:

- `DISCONNECTED → STREAMING` sin `CONNECTING`.
- `STREAMING → CONNECTING` sin detener/liberar sesión activa.
- `ERROR → STREAMING` sin reapertura válida.
- `STOPPING → STREAMING`.
- recuperación automática posterior a una desconexión explícita del usuario.

---

## 11. Modelo de datos

### 11.1. CameraDevice

```text
CameraDevice
- id: str
- index: int
- display_name: str
- available: bool
```

Semántica:

| Campo | Nullable | Unidad | Regla |
|---|---:|---|---|
| id | No | — | Identificador estable dentro de la sesión de descubrimiento |
| index | No | índice | >= 0 |
| display_name | No | — | Ej. `Cámara 0` |
| available | No | bool | Resultado de descubrimiento lógico |

No se exige nombre comercial real en SPEC-00.

### 11.2. CameraBackend

Modelo conceptual:

```text
CameraBackend
- AUTO
- backend específico soportado por adapter/configuración futura
```

`AUTO` es el valor inicial aprobado.

La lista concreta de backends expuestos en UI podrá ampliarse sin modificar dominio, siempre que no se añadan dependencias nuevas sin autorización.

### 11.3. CaptureConfiguration

```text
CaptureConfiguration
- device_index: int
- backend: CameraBackend
- requested_width: int?
- requested_height: int?
- requested_fps: float?
```

Para SPEC-00 inicial:

```text
requested_width = null
requested_height = null
requested_fps = null
```

significa:

> utilizar negociación/default del dispositivo/backend.

### 11.4. CaptureProperties

```text
CaptureProperties
- width: int?
- height: int?
- reported_fps: float?
- backend_name: str?
```

Los campos pueden ser `null` cuando el backend no proporcione información fiable.

### 11.5. Frame

Concepto de dominio/aplicación para una imagen capturada:

```text
Frame
- sequence: int
- captured_at: datetime
- width: int
- height: int
- image: objeto de imagen controlado por adapter/application
```

Restricciones:

- `sequence >= 0`;
- `width > 0`;
- `height > 0`;
- imagen no vacía.

El dominio no debe depender innecesariamente del tipo concreto `numpy.ndarray`.

### 11.6. CapturedFrame

```text
CapturedFrame
- source_sequence: int
- captured_at: datetime
- image_copy: objeto de imagen
```

Es efímero en SPEC-00.

### 11.7. CameraRuntimeState

```text
CameraRuntimeState
- state: CameraState
- selected_device: CameraDevice?
- properties: CaptureProperties?
- last_frame_at: datetime?
- last_error: CameraError?
- recovering: bool
```

---

## 12. Interfaces / Ports

### 12.1. CameraPort

Contrato conceptual, no implementación productiva obligatoria en esta sección:

```python
from typing import Protocol

class CameraPort(Protocol):
    def discover(self) -> list["CameraDevice"]:
        ...

    def open(self, config: "CaptureConfiguration") -> "CaptureProperties":
        ...

    def read(self) -> "Frame | None":
        ...

    def close(self) -> None:
        ...

    @property
    def is_open(self) -> bool:
        ...
```

Responsabilidades:

- descubrir cámaras;
- abrir un dispositivo;
- entregar frames;
- cerrar dispositivo;
- exponer estado básico.

No debe:

- detectar el gancho;
- calibrar;
- estimar coordenadas;
- publicar WebSocket;
- persistir SQLite.

### 12.2. FrameProvider / LatestFrameStore

Contrato interno recomendado:

```text
publish(frame)
latest() -> Frame?
snapshot() -> CapturedFrame?
clear()
```

Su responsabilidad es mantener un único frame vigente.

No debe crecer como cola ilimitada.

### 12.3. CameraController / Application Service

Responsabilidades:

- coordinar acciones de UI;
- invocar `CameraPort`;
- exponer estado;
- iniciar/detener worker;
- aplicar política de recuperación;
- producir cambios observables para Presentation.

La UI no debe operar directamente sobre `cv2.VideoCapture`.

---

## 13. Adapters

### 13.1. OpenCvCamera

Implementa:

```text
CameraPort
   ↓
OpenCvCamera
   ↓
cv2.VideoCapture
```

Responsabilidades:

- crear `VideoCapture`;
- aplicar backend;
- abrir índice;
- consultar propiedades;
- leer frame;
- liberar recurso;
- traducir fallos tecnológicos a errores de aplicación/dominio.

### 13.2. FakeCamera

Adapter de prueba.

Debe poder simular:

- descubrimiento de 0 cámaras;
- una cámara;
- múltiples cámaras;
- apertura exitosa;
- apertura fallida;
- frames válidos;
- frames inválidos;
- desconexión durante streaming;
- recuperación exitosa;
- recuperación fallida.

### 13.3. Qt Presentation Adapter

Componentes PySide6 deben convertir estados del controlador en:

- botones;
- selectores;
- labels;
- video;
- mensajes de error;
- placeholders.

---

## 14. Flujo técnico

### 14.1. Inicio

```text
main.py
  │
  ▼
bootstrap
  │
  ├── config
  ├── logging
  ├── adapters
  ├── application services
  └── presentation
        │
        ▼
MainWindow
        │
        ▼
LIVE
(camera disconnected)
```

### 14.2. Captura

```text
Usuario
   │ conectar
   ▼
LIVE
   │
   ▼
CameraController
   │
   ▼
CameraPort
   │
   ▼
OpenCvCamera
   │
   ▼
cv2.VideoCapture
   │
   ▼
Camera Worker
   │
   ▼
LatestFrameStore
   │
   ▼
signal/notification
   │
   ▼
LIVE renderer
```

### 14.3. Backpressure

```text
Camera Worker
   │
   ├── frame 100 ─────┐
   │                  ▼
   │             latest = 100
   │
   ├── frame 101 ─────┐
   │                  ▼
   │             latest = 101
   │             frame 100 pending is obsolete
   │
   └── frame 102 ─────> latest = 102
```

No existe cola creciente de frames.

### 14.4. Captura puntual

```text
Usuario
  │
  ▼
Capturar frame
  │
  ▼
LatestFrameStore.snapshot()
  │
  ▼
CapturedFrame en memoria
  │
  └── NO filesystem
      NO SQLite
```

---

## 15. Concurrencia

### 15.1. Main/UI Thread

Responsable de:

- event loop Qt;
- navegación;
- renderizado;
- interacción;
- actualización visual;
- recepción de señales ligeras.

No debe ejecutar:

- loop continuo `VideoCapture.read()`;
- procesamiento pesado;
- inferencia;
- operaciones largas.

### 15.2. Camera Worker

Responsable de:

- lectura continua de cámara;
- validación mínima de frame;
- actualización de latest frame;
- detección de fallo de captura;
- señalización de eventos.

### 15.3. Ownership

Reglas:

1. `OpenCvCamera` deberá ser utilizado de forma coherente por el componente de captura propietario.
2. La UI no llamará directamente `read()`.
3. El lifecycle de la cámara se coordinará desde Application.
4. El frame publicado hacia UI deberá transferirse de forma segura respecto a mutabilidad/vida útil.
5. Una captura puntual deberá ser una copia coherente y no una referencia mutable que pueda sobrescribirse durante el siguiente frame.

### 15.4. Buffer

Política:

```text
capacidad lógica = 1 frame vigente
```

### 15.5. Backpressure

No se bloquea la captura para obligar a UI a consumir todos los frames.

Se reemplaza el frame pendiente.

### 15.6. Cancelación

Eventos que deben poder cancelar captura:

- usuario desconecta;
- aplicación cierra;
- error no recuperable;
- inicio de recuperación.

### 15.7. Multiprocessing

No se introduce en SPEC-00.

---

## 16. Manejo de errores

| Error | Detección | Reacción | Recuperación | Estado posterior | Log |
|---|---|---|---|---|---|
| Sin cámaras | discover vacío | Mostrar empty state | Refresh manual | DISCONNECTED | INFO |
| Cámara ocupada | open falla | Mostrar error | Retry/manual | ERROR | WARNING |
| Backend inválido/no disponible | open falla | Informar | Cambiar configuración/manual | ERROR | ERROR |
| Primer frame inválido | read inválido | Abort connection | Retry | ERROR/RECOVERING según contexto | WARNING |
| Frame aislado inválido | read inválido | No publicar | Continuar según política | STREAMING o RECOVERING | WARNING |
| Cámara desconectada | lecturas fallidas/pérdida | Detener sesión defectuosa | Recuperación limitada | RECOVERING | WARNING |
| Recuperación agotada | política termina | Detener intentos | Retry manual | ERROR | ERROR |
| Error renderizando frame | excepción Presentation | No cerrar captura automáticamente salvo incompatibilidad real | Mostrar error técnico | STREAMING o ERROR UI | ERROR |
| Error al cerrar dispositivo | close/release falla | Continuar shutdown lógico | Ninguna | DISCONNECTED | WARNING |
| Excepción no controlada en worker | error worker | Notificar controller | detener worker | ERROR | ERROR |

Reglas adicionales:

- ningún error debe generar coordenadas;
- ningún error debe generar movimiento físico;
- ningún error debe ocultarse silenciosamente si afecta operación;
- la aplicación debe intentar mantener la UI operativa.

---

## 17. Observabilidad

### 17.1. Logging base

Niveles:

```text
INFO
WARNING
ERROR
```

Eventos mínimos:

- application_started;
- application_closing;
- camera_discovery_started;
- camera_discovery_completed;
- camera_selected;
- camera_connecting;
- camera_connected;
- camera_disconnected_by_user;
- camera_lost;
- camera_recovery_started;
- camera_recovery_succeeded;
- camera_recovery_exhausted;
- camera_error.

### 17.2. Métricas de SPEC-00

Registrar o exponer cuando sea técnicamente viable:

- camera reported FPS;
- measured capture FPS;
- frames captured;
- invalid frames;
- replaced/dropped stale frames;
- camera reconnect attempts;
- last valid frame timestamp.

Los umbrales objetivo permanecen:

```text
TBD — definir mediante benchmark
```

---

## 18. UI/UX

### 18.1. Dirección visual

La aplicación tendrá apariencia de:

> Consola industrial/técnica de visión.

Reglas:

- fondo principal negro;
- superficies secundarias oscuras;
- alto contraste;
- texto legible;
- jerarquía visual simple;
- video como elemento principal en LIVE;
- estados visibles;
- evitar ornamentación que reduzca legibilidad.

### 18.2. Ventana principal

Comportamiento:

- inicia maximizada;
- permite redimensionar;
- no fuerza fullscreen;
- sidebar izquierdo persistente;
- área central de contenido.

### 18.3. Sidebar

Orden inicial:

```text
LIVE
CALIBRACIÓN
DETECCIÓN
ANALÍTICA
REPORTES
DIAGNÓSTICOS
AJUSTES
```

Todos visibles desde SPEC-00.

### 18.4. Placeholder de módulos futuros

Ejemplo conceptual:

```text
CALIBRACIÓN

Módulo preparado.
La funcionalidad se implementará en SPEC-01.
```

No debe simular datos ni implementar lógica futura.

### 18.5. LIVE

Estructura conceptual:

```text
┌──────────────────────────────────────────────────────────────┐
│ BLANQUITA VISION                                             │
├──────────────┬───────────────────────────────────────────────┤
│ LIVE         │                                               │
│ CALIBRACIÓN  │                VIDEO                          │
│ DETECCIÓN    │                                               │
│ ANALÍTICA    │                                               │
│ REPORTES     │                                               │
│ DIAGNÓSTICOS │                                               │
│ AJUSTES      │                                               │
│              ├───────────────────────────────────────────────┤
│              │ Cámara: Cámara 0                              │
│              │ Estado: STREAMING                             │
│              │ Resolución: efectiva                          │
│              │ FPS: efectivo/reportado                      │
│              │ Backend: AUTO / efectivo                     │
│              │                                               │
│              │ [Actualizar] [Conectar] [Desconectar]        │
│              │ [Capturar frame] [Reintentar]                │
└──────────────┴───────────────────────────────────────────────┘
```

### 18.6. Estados visuales LIVE

#### DISCONNECTED

- área de video sin contenido activo;
- selector habilitado;
- actualizar habilitado;
- conectar habilitado si existe selección;
- desconectar deshabilitado;
- capturar deshabilitado.

#### DISCOVERING

- indicador de actividad;
- evitar doble refresh simultáneo.

#### CONNECTING

- indicar conexión;
- evitar múltiples aperturas simultáneas.

#### STREAMING

- video visible;
- desconectar habilitado;
- capturar frame habilitado;
- selector de cámara bloqueado o protegido contra cambios incompatibles durante sesión.

#### RECOVERING

- conservar UI operativa;
- informar recuperación;
- no mostrar un frame antiguo como si fuera actual sin señalización.

#### ERROR

- mostrar error legible;
- mostrar `Reintentar`;
- permitir actualizar cámaras.

### 18.7. Empty state

Cuando no existen cámaras:

```text
No se detectaron cámaras disponibles.

[Actualizar cámaras]
```

---

## 19. Seguridad

### 19.1. Separación física

SPEC-00 no crea:

- WebSocket al ESP32;
- HTTP al ESP32;
- TCP de control;
- MQTT;
- serial de control.

### 19.2. Datos de cámara

Un frame es información de percepción.

No equivale a:

```text
movimiento autorizado
```

### 19.3. Recursos

La aplicación deberá:

- liberar cámara;
- evitar loops de reintento ilimitados;
- evitar buffers ilimitados;
- validar frames antes de usarlos.

### 19.4. Paths

SPEC-00 no persiste capturas, por lo que no define rutas de imágenes productivas.

Las rutas de persistencia se definirán en SPEC-02.

---

## 20. Persistencia

### 20.1. Persistencia productiva en SPEC-00

No se implementa persistencia de:

- frames;
- capturas;
- sesiones;
- detecciones;
- reportes;
- eventos históricos.

### 20.2. Configuración

SPEC-00 puede definir estructuras de configuración en memoria/infraestructura necesarias para iniciar la aplicación.

La persistencia definitiva en SQLite pertenece a SPEC-02.

### 20.3. Captura puntual

`CapturedFrame` permanece en memoria.

SPEC-02 definirá:

```text
CapturedFrame
      ↓
filesystem
      +
metadata
      ↓
SQLite
```

---

## 21. Testing obligatorio

### TC-00-001 — Arranque en LIVE sin cámara automática

**Objetivo:** Verificar inicio seguro.

**Precondiciones:** Aplicación instalable/ejecutable.

**Datos:** Ninguno.

**Procedimiento:**

1. Iniciar aplicación.
2. Observar pantalla activa.
3. Verificar estado de cámara.

**Resultado esperado:**

- LIVE visible.
- CameraState = DISCONNECTED.
- No existe captura activa.

**Tipo:** Integration test / UI smoke test.

---

### TC-00-002 — Navegación completa

**Objetivo:** Verificar shell.

**Procedimiento:** Seleccionar cada elemento del sidebar.

**Resultado esperado:** Cada pantalla se muestra; módulos futuros presentan placeholder.

**Tipo:** Integration test.

---

### TC-00-003 — FakeCamera descubre dispositivos

**Objetivo:** Validar descubrimiento desacoplado.

**Entrada:** FakeCamera con índices 0 y 2 disponibles.

**Resultado esperado:** UI/controller recibe dos dispositivos.

**Tipo:** Unit test.

---

### TC-00-004 — Sin cámaras disponibles

**Entrada:** FakeCamera devuelve lista vacía.

**Resultado esperado:** Empty state; aplicación operativa.

**Tipo:** Unit + integration negative test.

---

### TC-00-005 — Selección no conecta

**Objetivo:** Verificar separación selección/apertura.

**Procedimiento:** Seleccionar cámara.

**Resultado esperado:** `open()` no ha sido invocado.

**Tipo:** Unit test.

---

### TC-00-006 — Apertura manual exitosa

**Entrada:** FakeCamera abre correctamente.

**Resultado esperado:** CONNECTING → STREAMING.

**Tipo:** Unit/integration test.

---

### TC-00-007 — Apertura fallida

**Entrada:** FakeCamera lanza error de apertura.

**Resultado esperado:** CONNECTING → ERROR; UI operativa.

**Tipo:** Negative test.

---

### TC-00-008 — Resolución/FPS no forzados inicialmente

**Objetivo:** Verificar negociación del dispositivo.

**Entrada:** configuración con width/height/fps `null`.

**Resultado esperado:** Adapter no impone valores arbitrarios.

**Tipo:** Unit test.

---

### TC-00-009 — Mostrar propiedades efectivas

**Entrada:** FakeCamera retorna 1280x720 y FPS reportado.

**Resultado esperado:** Estado expone esos valores sin asumir otros.

**Tipo:** Unit/UI integration test.

Nota: Los valores utilizados en el fake son datos de prueba, no baseline del producto.

---

### TC-00-010 — Latest-frame reemplaza frame pendiente

**Entrada:** frames 1, 2 y 3 producidos antes de consumo.

**Resultado esperado:** consumidor obtiene frame 3; buffer no acumula 1/2.

**Tipo:** Unit test.

---

### TC-00-011 — Frame inválido no se publica

**Entrada:** lectura vacía.

**Resultado esperado:** latest frame no se reemplaza por dato inválido; se registra evento.

**Tipo:** Negative test.

---

### TC-00-012 — Desconexión inesperada inicia recuperación

**Entrada:** cámara válida que falla durante streaming.

**Resultado esperado:** STREAMING → RECOVERING.

**Tipo:** Unit/integration test.

---

### TC-00-013 — Recuperación exitosa

**Entrada:** FakeCamera falla y vuelve a estar disponible dentro de política.

**Resultado esperado:** RECOVERING → STREAMING.

**Tipo:** Integration test.

---

### TC-00-014 — Recuperación agotada

**Entrada:** cámara permanece indisponible.

**Resultado esperado:** RECOVERING → ERROR y reintentos cesan.

**Tipo:** Negative/integration test.

---

### TC-00-015 — Retry manual

**Precondición:** ERROR.

**Trigger:** usuario pulsa Reintentar.

**Resultado esperado:** ERROR → CONNECTING.

**Tipo:** Integration test.

---

### TC-00-016 — Desconexión manual no auto-recupera

**Entrada:** usuario detiene cámara.

**Resultado esperado:** STREAMING → STOPPING → DISCONNECTED; no RECOVERING.

**Tipo:** Unit/integration test.

---

### TC-00-017 — Snapshot efímero

**Entrada:** latest frame válido.

**Procedimiento:** solicitar captura.

**Resultado esperado:**

- se obtiene CapturedFrame;
- es una copia coherente;
- no se crea archivo;
- no se usa SQLite.

**Tipo:** Unit test.

---

### TC-00-018 — Snapshot sin frame

**Entrada:** cámara desconectada.

**Resultado esperado:** acción rechazada/controlada; no crash.

**Tipo:** Negative test.

---

### TC-00-019 — Cierre con cámara activa

**Objetivo:** Verificar lifecycle.

**Procedimiento:** iniciar streaming y cerrar app.

**Resultado esperado:** worker finaliza y cámara se libera.

**Tipo:** Integration test.

---

### TC-00-020 — FakeCamera sustituye adapter real

**Objetivo:** Verificar Ports & Adapters.

**Resultado esperado:** Application puede operar sin importar OpenCV concreto.

**Tipo:** Architecture/unit test.

---

### TC-00-021 — Test con cámara USB real

**Objetivo:** Confirmar apertura, frames y cierre sobre hardware objetivo.

**Precondiciones:** Webcam USB física conectada.

**Procedimiento:**

1. iniciar app;
2. actualizar cámaras;
3. seleccionar índice;
4. conectar;
5. observar video;
6. desconectar;
7. cerrar.

**Resultado esperado:** flujo completo sin crash y recurso liberado.

**Tipo:** TEST CON HARDWARE REAL.

**Estado actual:** VALIDADO EN HARDWARE mediante prueba manual del usuario: reconocimiento, conexión, video, desconexión y conexión manual, todos los botones del frontend y cierre con cámara activa seguido de reapertura y conexión satisfactorias. La prueba automatizada opcional con hardware no fue ejecutada por el agente. Véase el registro de la sección 28.

---

### TC-00-022 — Desconexión física durante streaming

**Objetivo:** Validar recuperación real.

**Precondiciones:** Webcam USB real.

**Procedimiento:** retirar dispositivo durante streaming.

**Resultado esperado:** RECOVERING y posteriormente recuperación o ERROR según disponibilidad.

**Tipo:** TEST CON HARDWARE REAL.

**Estado actual:** FALLIDO EN HARDWARE; LIMITACIÓN CONOCIDA ACEPTADA POR EL USUARIO para cerrar SPEC-00. La detección y recuperación automática de retirada USB con DSHOW no funcionan correctamente. El usuario acepta recuperar mediante Desconectar, reconectar físicamente la cámara y Conectar. Este caso no se registra como satisfactorio; véanse INC-00-001 y DEC-00-014 en la sección 28.

---

### TC-00-023 — Benchmark base de captura

**Objetivo:** Obtener evidencia para objetivos de rendimiento futuros.

**Medir:**

- FPS capturados;
- frames descartados;
- uso aproximado CPU;
- estabilidad UI;
- latencia visual observable/instrumentable.

**Resultado esperado:** datos registrados para definir objetivos posteriores.

**Tipo:** Performance test.

**Criterio numérico:** TBD — benchmark.

**Estado actual:** NO EJECUTADO, confirmado por el usuario. Las mediciones permanecen pendientes como seguimiento documental tras el cierre solicitado de SPEC-00. No se acreditan resultados de benchmark ni se fijan objetivos numéricos; véase la sección 28.8.

---

## 22. Criterios de aceptación

### AC-00-001

**DADO** BLANQUITA Vision instalado correctamente  
**CUANDO** el usuario inicia la aplicación  
**ENTONCES** se abre maximizada, redimensionable, con LIVE visible y cámara desconectada.

### AC-00-002

**DADO** el shell iniciado  
**CUANDO** el usuario navega por el sidebar  
**ENTONCES** los siete módulos V1 están disponibles visualmente y los no implementados presentan placeholder.

### AC-00-003

**DADO** una lista actualizable de cámaras  
**CUANDO** el sistema descubre índices disponibles  
**ENTONCES** los presenta como `Cámara N` sin requerir nombre comercial.

### AC-00-004

**DADO** una cámara seleccionada  
**CUANDO** el usuario no pulsa conectar  
**ENTONCES** la cámara permanece cerrada.

### AC-00-005

**DADO** una cámara compatible  
**CUANDO** el usuario pulsa conectar  
**ENTONCES** el sistema abre el dispositivo mediante `CameraPort` y entra en STREAMING si recibe frames válidos.

### AC-00-006

**DADO** la primera apertura de cámara  
**CUANDO** no se solicitó resolución/FPS concretos  
**ENTONCES** el sistema no impone valores arbitrarios y expone propiedades efectivas.

### AC-00-007

**DADO** streaming activo  
**CUANDO** los frames llegan más rápido que su consumo  
**ENTONCES** solo se conserva el frame más reciente y la memoria no acumula una cola creciente.

### AC-00-008

**DADO** streaming activo  
**CUANDO** la cámara se pierde inesperadamente  
**ENTONCES** el sistema intenta recuperación limitada sin bloquear la UI.

### AC-00-009

**DADO** recuperación agotada  
**CUANDO** la cámara continúa indisponible  
**ENTONCES** el sistema queda en ERROR y ofrece Reintentar.

### AC-00-010

**DADO** streaming activo  
**CUANDO** el usuario desconecta manualmente  
**ENTONCES** el dispositivo se libera y no comienza recuperación automática.

### AC-00-011

**DADO** un latest frame válido  
**CUANDO** el usuario solicita captura puntual  
**ENTONCES** se crea un CapturedFrame en memoria y no se persiste ningún archivo.

### AC-00-012

**DADO** la aplicación con cámara activa  
**CUANDO** el usuario cierra la ventana  
**ENTONCES** se detiene el worker y se libera la cámara.

### AC-00-013

**DADO** el código de dominio  
**CUANDO** se inspeccionan dependencias  
**ENTONCES** no contiene acoplamiento directo a PySide6/cv2 para responsabilidades abstraídas.

### AC-00-014

**DADO** el entorno del proyecto  
**CUANDO** se instalan dependencias  
**ENTONCES** `pyproject.toml` y `uv.lock` actúan como fuente de verdad y `requirements.txt` se mantiene como export compatible.

### AC-00-015

**DADO** la interfaz principal  
**CUANDO** se visualiza cualquier pantalla  
**ENTONCES** mantiene un diseño negro, técnico y de alto contraste.

---

## 23. Definition of Done

SPEC-00 podrá pasar a `IMPLEMENTED` cuando:

```text
✓ entorno Python/uv reproducible
✓ .venv utilizado localmente
✓ pyproject.toml correcto
✓ uv.lock generado
✓ requirements.txt exportable/consistente
✓ estructura arquitectónica creada
✓ shell PySide6 operativo
✓ sidebar operativo
✓ LIVE inicial
✓ placeholders creados
✓ CameraPort implementado
✓ OpenCvCamera implementado
✓ FakeCamera disponible
✓ descubrimiento de cámaras operativo
✓ selección operativa
✓ conexión manual operativa
✓ desconexión operativa
✓ latest-frame operativo
✓ video en vivo operativo
✓ captura efímera operativa
✓ recuperación limitada implementada
✓ errores principales gestionados
✓ shutdown libera recursos
✓ tests automatizables definidos y pasando
✓ documentación actualizada
✓ sin funcionalidades de SPEC-01/02/03 adelantadas
✓ sin comunicación directa a ESP32
✓ sin acciones Git realizadas por agentes
```

### 23.1. VALIDADO EN SOFTWARE

Requiere:

- tests unitarios;
- tests integración automatizables;
- tests negativos;
- arquitectura verificada.

### 23.2. VALIDADO EN HARDWARE

Requiere adicionalmente:

- cámara USB real;
- video estable;
- desconexión/reconexión real;
- cierre y liberación de hardware.

No deberá declararse `VALIDATED` en hardware solo con FakeCamera.

El cierre actual de SPEC-00 registra pruebas manuales con cámara física realizadas por el usuario y una excepción explícitamente aceptada para la recuperación automática ante retirada USB (DEC-00-014). El resultado fallido de TC-00-022 se conserva en el registro y no se transforma en una prueba satisfactoria.

---

## 24. Dependencias con otras SPECS

### DEPENDE DE

```text
Ninguna SPEC anterior.
```

Depende documentalmente de:

- AGENTS.md
- VISION_INTELIGENTE_BLQ.md
- ARQUITECTURA_CONEXION.md
- APP_MOVIL_BLANQ_V2.md

### DESBLOQUEA

#### SPEC-01

Proporciona:

- CameraPort;
- OpenCvCamera;
- Frame;
- LatestFrame;
- worker de captura;
- LIVE;
- arquitectura base;
- UI;
- lifecycle de cámara.

SPEC-01 podrá construir:

```text
Frame
  ↓
Preprocess
  ↓
Calibration
  ↓
Detection
  ↓
Tracking
  ↓
Position Estimation
```

#### SPEC-02

Proporciona:

- CapturedFrame efímero;
- shell para Reports/Diagnostics/Settings;
- eventos base;
- configuración base.

SPEC-02 añadirá:

- WebSocket;
- SQLite;
- filesystem de capturas;
- reportes;
- analítica;
- diagnósticos.

#### SPEC-03

Reutilizará:

- ports;
- adapters;
- UI;
- testing/fakes;
- concurrencia;
- métricas base.

### NO DEBE MODIFICAR

SPEC-00 no debe definir de forma definitiva:

- algoritmo de calibración;
- detector del gancho;
- algoritmo de estimación X/Y/Z;
- estructura final de VisionReport;
- protocolo WebSocket;
- esquema SQLite;
- modelo ONNX;
- proceso de release final.

---

## 25. Decisiones abiertas

### OPEN-00-001 — Parámetros exactos de recuperación

**Pregunta:**  
¿Cuántos intentos automáticos y qué intervalo/backoff deben utilizarse para recuperar una cámara perdida?

**Motivo:**  
El comportamiento general ya está aprobado como recuperación limitada, pero no existe evidencia para fijar valores numéricos.

**Impacto:**  
Afecta tiempos de recuperación, UX y pruebas temporales.

**Momento en que debe resolverse:**  
Antes de marcar SPEC-00 como `APPROVED` para implementación o durante una revisión específica basada en pruebas del hardware.

**Estado:** RESUELTO por aprobación explícita del usuario durante implementación.

**Decisión:** Tres intentos automáticos, separados por dos segundos. Parámetros iniciales pendientes de validación con hardware.

---

### OPEN-00-002 — Rango de índices durante descubrimiento OpenCV

**Pregunta:**  
¿Cuál será el límite práctico de índices que `OpenCvCamera` probará al actualizar cámaras?

**Motivo:**  
OpenCV no proporciona de forma portable, usando solo `VideoCapture`, una enumeración universal de dispositivos con nombres comerciales.

**Impacto:**  
Afecta duración del descubrimiento y cobertura de dispositivos.

**Momento en que debe resolverse:**  
Antes de implementación final del descubrimiento.

**Estado:** RESUELTO por aprobación explícita del usuario durante implementación.

**Decisión:** Probar índices de 0 a 9 inclusive, con liberación de cada dispositivo temporal.

---

### OPEN-00-003 — Exposición de backends específicos en UI

**Pregunta:**  
¿AJUSTES debe exponer desde SPEC-00 una lista seleccionable de backends concretos de Windows o solo `AUTO` hasta que exista evidencia de compatibilidad?

**Motivo:**  
La arquitectura configurable ya está aprobada, pero no se ha aprobado un catálogo concreto de backends en UI.

**Impacto:**  
Afecta Settings y pruebas hardware.

**Momento en que debe resolverse:**  
Puede resolverse durante implementación de ajustes de captura sin modificar `CameraPort`.

**Estado:** RESUELTO por aprobación explícita del usuario durante implementación.

**Decisión:** Backend configurable mediante argumento de arranque, AUTO por defecto. AJUSTES permanece como placeholder. Los identificadores se resuelven en infraestructura/adapter, sin constantes OpenCV en dominio.

---

### OPEN-00-004 — Formato de exportación de requirements.txt

**Pregunta:**  
Definir el comando exacto y política de regeneración de `requirements.txt` a partir del lockfile.

**Motivo:**  
Se incorporó `requirements.txt` por solicitud del usuario, pero la fuente de verdad permanece `pyproject.toml + uv.lock`.

**Impacto:**  
Reproducibilidad y mantenimiento de dependencias.

**Momento en que debe resolverse:**  
Antes de aprobar el workflow definitivo de entorno.

**Estado:** RESUELTO por aprobación explícita del usuario durante implementación.

**Decisión:** `uv export --locked --format requirements-txt --no-emit-project --output-file requirements.txt`. Incluir el grupo de desarrollo con pytest (grupo predeterminado de uv) y regenerar después de cada cambio aprobado del lockfile.

---

## 26. Riesgos

### RISK-00-001 — Enumeración de cámaras dependiente del backend

**Descripción:**  
Probar índices mediante OpenCV puede comportarse de forma distinta según drivers/backend.

**Probabilidad:** Media.

**Impacto:** Medio.

**Mitigación:**  
Encapsular descubrimiento en adapter; permitir refresh manual; validar hardware real; no acoplar dominio al mecanismo.

---

### RISK-00-002 — Cámara ocupada por otra aplicación

**Descripción:**  
Windows u otra app puede mantener la cámara en uso.

**Probabilidad:** Media.

**Impacto:** Medio.

**Mitigación:**  
Error explícito, UI operativa, Retry manual, logs.

---

### RISK-00-003 — UI bloqueada por captura

**Descripción:**  
Un loop de cámara en Main Thread congelaría la interfaz.

**Probabilidad:** Baja si se respeta arquitectura.

**Impacto:** Alto.

**Mitigación:**  
Camera Worker obligatorio y tests de integración.

---

### RISK-00-004 — Acumulación de frames

**Descripción:**  
Una cola ilimitada generaría latencia creciente y consumo de memoria.

**Probabilidad:** Baja con diseño aprobado.

**Impacto:** Alto.

**Mitigación:**  
Latest-frame con capacidad lógica 1.

---

### RISK-00-005 — Recursos de cámara no liberados

**Descripción:**  
Errores de lifecycle pueden dejar dispositivo bloqueado.

**Probabilidad:** Media.

**Impacto:** Alto.

**Mitigación:**  
Shutdown explícito, `close/release`, tests de cierre, hardware test.

---

### RISK-00-006 — Divergencia requirements / lockfile

**Descripción:**  
Mantener manualmente `requirements.txt`, `pyproject.toml` y `uv.lock` podría generar inconsistencias.

**Probabilidad:** Alta si se editan manualmente múltiples fuentes.

**Impacto:** Medio.

**Mitigación:**  
`pyproject.toml + uv.lock` son fuente de verdad; `requirements.txt` solo export derivado y no debe editarse como fuente paralela.

---

### RISK-00-007 — FPS reportado no representa FPS real

**Descripción:**  
Algunos drivers reportan propiedades imprecisas.

**Probabilidad:** Media.

**Impacto:** Bajo/Medio.

**Mitigación:**  
Distinguir FPS reportado de FPS medido; benchmark posterior.

---

### RISK-00-008 — Recuperación demasiado agresiva o lenta

**Descripción:**  
Sin medición física, valores arbitrarios de retry pueden degradar UX.

**Probabilidad:** Media.

**Impacto:** Medio.

**Mitigación:**  
OPEN-00-001; medir antes de fijar parámetros.

---

## 27. Trazabilidad

| Requisito | Caso de uso | Test principal | Criterio aceptación |
|---|---|---|---|
| RF-00-001 a RF-00-008 | UC-00-01 | TC-00-001 | AC-00-014 |
| RF-00-009 a RF-00-018 | UC-00-01, UC-00-02 | TC-00-001, TC-00-002 | AC-00-001, AC-00-002, AC-00-015 |
| RF-00-019 a RF-00-024 | UC-00-03, UC-00-04 | TC-00-003, TC-00-004, TC-00-005, TC-00-020 | AC-00-003, AC-00-004, AC-00-013 |
| RF-00-025 a RF-00-034 | UC-00-05 | TC-00-006 a TC-00-009, TC-00-021 | AC-00-005, AC-00-006 |
| RF-00-035 a RF-00-045 | UC-00-06 | TC-00-010, TC-00-011, TC-00-023 | AC-00-007 |
| RF-00-046 a RF-00-051 | UC-00-08, UC-00-09 | TC-00-012 a TC-00-015, TC-00-022 | AC-00-008, AC-00-009 |
| RF-00-052 a RF-00-055 | UC-00-10 | TC-00-017, TC-00-018 | AC-00-011 |
| RF-00-056 a RF-00-058 | UC-00-07, UC-00-11 | TC-00-016, TC-00-019 | AC-00-010, AC-00-012 |
| RNF-00-001, RNF-00-002 | UC-00-03 a UC-00-08 | TC-00-021, TC-00-022 | AC-00-003, AC-00-005 |
| RNF-00-003 a RNF-00-006 | Todos | TC-00-020 | AC-00-013 |
| RNF-00-007 a RNF-00-011 | UC-00-06 | TC-00-010, TC-00-023 | AC-00-007 |
| RNF-00-012 a RNF-00-014 | UC-00-06 a UC-00-11 | TC-00-011 a TC-00-019 | AC-00-008 a AC-00-012 |
| RNF-00-015 a RNF-00-018 | Todos | revisión estática + tests | AC-00-013 |
| RNF-00-019 a RNF-00-022 | UC-00-01, UC-00-02, UC-00-06 | TC-00-001, TC-00-002 | AC-00-001, AC-00-002, AC-00-015 |
| RNF-00-023, RNF-00-024 | Todos | revisión arquitectónica | AC-00-013 |

---

## 28. Registro de implementación y validación

### 28.1. Estado de implementación

SPEC-00 pasa de APPROVED a **IMPLEMENTED** mediante esta actualización documental solicitada por el usuario tras confirmar el funcionamiento del programa.

Posteriormente, el usuario solicitó dejar la SPEC terminada y validada, confirmó cierre/reapertura con cámara activa y aceptó explícitamente la recuperación manual como solución a la limitación de retirada USB. El estado final pasa a **VALIDATED**, con el alcance, la excepción y el benchmark no ejecutado registrados en la sección 28.8.

La fundación, shell, LIVE, CameraPort/OpenCvCamera, latest-frame, captura efímera, recuperación limitada y shutdown fueron implementados. La documentación operativa y las instrucciones de prueba se encuentran en `README.md`.

### 28.2. Validación automatizada previa

Verificación realizada durante implementación el 6 de octubre de 2026:

- `uv lock --check`: correcto.
- `uv run --locked python -m pytest -q`: **41 passed, 1 skipped**.
- Casos automatizables TC-00-001 a TC-00-020 cubiertos con fakes, integración Qt y revisión arquitectónica automatizada.
- La prueba opcional con cámara real fue omitida al no indicarse un índice físico.
- Arranque/cierre del punto de entrada y funcionamiento del benchmark comprobados en software; esa comprobación del benchmark no constituye una medición de hardware.

### 28.3. Confirmación manual del usuario

**Fecha de registro:** 6 de octubre de 2026.  
**Responsable de la prueba:** usuario operador.  
**Fuente:** reporte explícito del usuario en la conversación y solicitud de actualizar la documentación.

Resultados confirmados:

1. Conexión de cámara física y reconocimiento correcto del dispositivo por el programa.
2. Funcionamiento satisfactorio del programa con la cámara conectada.
3. Revisión visual y funcional del frontend con resultado satisfactorio.
4. En un reporte posterior, funcionamiento correcto de todos los botones, incluidos Conectar y Desconectar; desconexión y conexión manual satisfactorias.
5. Confirmación final del funcionamiento correcto del programa y de la interfaz después de corregir la barra inferior; solicitud expresa de terminar y validar SPEC-00.
6. Cierre de ventana con video activo y posterior reapertura/conexión de cámara satisfactorios, confirmados explícitamente por el usuario.
7. Confirmación de que la retirada física USB todavía no funciona correctamente y aceptación explícita de recuperar mediante Desconectar/Conectar, sin dedicar más tiempo a corregirla en esta SPEC.
8. Confirmación de que el benchmark real no fue ejecutado.

En un reporte anterior, el usuario informó que la retirada física USB durante captura no cambia automáticamente el estado conectado ni permite recuperar automáticamente la captura al reinsertar el USB. Al solicitar el cierre confirmó que el fallo persiste y aceptó expresamente la recuperación manual. TC-00-022 permanece fallido y la incidencia se registra como limitación conocida aceptada, no como validación satisfactoria de recuperación automática.

La evidencia física fue aportada por el usuario. Los reportes iniciales cubrían parcialmente TC-00-021; la confirmación explícita de cierre/reapertura completa el flujo funcional manual con cámara real. No equivale a una ejecución física realizada por el agente ni a la prueba automatizada opcional con hardware.

El reconocimiento reportado corresponde al dispositivo de cámara; no acredita detección del gancho, calibración ni estimación de coordenadas, que pertenecen a SPEC-01.

### 28.4. Cobertura de validación y seguimiento

| Comprobación | Estado |
|---|---|
| TC-00-021: reconocimiento/conexión y funcionamiento de cámara real | Confirmado por el usuario |
| TC-00-021: desconexión y conexión manual | Confirmado por el usuario |
| TC-00-021: cierre de ventana y posterior reutilización de cámara | Confirmado explícitamente por el usuario |
| TC-00-022: retirada USB y recuperación/error real | Fallido; limitación aceptada para el cierre, DEC-00-014 |
| TC-00-023: benchmark de captura real | No ejecutado; mediciones pendientes como seguimiento |
| Compatibilidad física en Windows 10 y Windows 11 | Pendiente de registro en ambas plataformas |

El usuario confirmó posteriormente **DSHOW** como backend efectivo de la prueba fallida de retirada USB. No se han proporcionado modelo de cámara, resolución, FPS ni versión concreta de Windows; estos datos no se infieren.

**Conclusión:** VALIDADO EN SOFTWARE para los escenarios automatizados y VALIDADO EN HARDWARE para el flujo funcional manual confirmado por el usuario, con limitación conocida aceptada de retirada USB. El estado documental es **VALIDATED** por solicitud y aceptación del usuario. No se acredita recuperación automática física satisfactoria, benchmark ni compatibilidad comprobada en ambas versiones de Windows.

Las actualizaciones de este registro no modifican requisitos ni parámetros aprobados. La ejecución de software realizada al revisar la incidencia se documenta a continuación; las comprobaciones físicas fueron realizadas y reportadas por el usuario.

### 28.5. INC-00-001 — Pérdida USB no detectada durante captura

**Estado:** LIMITACIÓN CONOCIDA ACEPTADA PARA EL CIERRE DE SPEC-00; fallo técnico no corregido.  
**Fuente:** reporte de prueba física del usuario operador.  
**Caso afectado:** TC-00-022; detección de pérdida y recuperación de RF-00-046/RF-00-047 y AC-00-008.

**Resultado observado según el reporte:**

- Cámara inicialmente conectada y funcionando.
- Al retirar físicamente el USB, el programa permanece en estado conectado, sin transición observable a recuperación.
- Al volver a insertar el USB, no se recupera automáticamente la captura.
- Los botones de conexión y desconexión manual funcionan correctamente.
- En la ampliación del reporte, el usuario confirmó backend efectivo DSHOW. El contador Frames y Último frame siguen actualizándose muy lentamente después de retirar el USB, mientras la imagen permanece congelada en la última captura.
- Al probar explícitamente MSMF, el usuario reportó lista de cámaras vacía y «MSMF / efectivo: No disponible». El entorno comprobado registra MSMF pero no permite cargarlo (`hasBackend` = False); DSHOW está disponible (`hasBackend` = True).

**Resultado esperado:** tres lecturas inválidas consecutivas inician RECOVERING y una recuperación limitada. Si el dispositivo vuelve durante los intentos y entrega frames válidos, se retorna a STREAMING. Una vez agotados los intentos, se pasa a ERROR y se requiere Reintentar; no existe una espera de reconexión automática indefinida.

**Diagnóstico actualizado:** la implementación detecta pérdida a partir del resultado de `CameraPort.read()`. El incremento de Frames acredita que continúan publicándose lecturas aceptadas como válidas, a pesar de observarse la última imagen congelada. El timestamp se asigna al retornar la lectura, no a partir de un timestamp físico certificado por la cámara. El comportamiento es consistente con entrega repetida de la última imagen mediante DSHOW; no con un bloqueo permanente de toda la lectura, aunque existan esperas largas entre retornos.

La implementación no tiene detección independiente de presencia física USB o frescura certificada por el driver. La igualdad de imágenes no se utiliza como prueba de desconexión, porque una escena inmóvil también puede producir imágenes iguales.

**Resultado de la comparación de backends:** MSMF no descubrió cámaras en la prueba del usuario. La comprobación del entorno encontró que el backend está registrado pero no disponible para cargarlo; por tanto, la comparación de recuperación física con MSMF no pudo realizarse. La validación de disponibilidad se corrigió conforme a INC-00-002. La etiqueta «efectivo: No disponible» representa ausencia de sesión abierta, no prueba de que no exista una cámara física.

**Siguiente comprobación operativa:** volver a abrir con `--backend DSHOW`, actualizar dispositivos y conectar la cámara. Esto restaura la configuración previamente funcional y no constituye una corrección de la pérdida USB. No cambia AUTO como valor predeterminado ni habilita fallback silencioso.

**Decisión final del usuario:** el fallo persiste, pero se acepta recuperar pulsando Desconectar, reconectando físicamente la cámara y pulsando Conectar. El usuario solicitó no dedicar más tiempo a corregir esta condición y cerrar la SPEC. Se archiva para este cierre como limitación conocida aceptada mediante DEC-00-014; no se declara una solución automática ni se introduce una política nueva de timeout.

**Pruebas de software ejecutadas al revisar el reporte:**

```text
python -m pytest -q tests/integration/test_camera_lifecycle.py -k "loss_tc_013 or exhaustion_is_bounded or disconnect_during_recovery or cancel_blocked_operation"
5 passed, 12 deselected
```

Estas pruebas usan fakes y confirman recuperación a partir de lecturas inválidas, agotamiento, cancelación y bloqueo de descubrimiento/apertura. No reproducen una lectura de hardware bloqueada durante streaming ni acreditan que el fallo reportado esté resuelto.

### 28.6. INC-00-002 — Backend registrado pero no disponible

**Estado:** comprobación de disponibilidad corregida y validada en software.  
**Requisitos relacionados:** RF-00-028/RF-00-029 y manejo de backend inválido/no disponible de la sección 16.

**Hallazgo:** `OpenCvCamera.backend_id()` comprobaba el registro del backend, pero no su disponibilidad real. La consulta del entorno mediante OpenCV 4.14.0 reportó DSHOW registrado y disponible, y MSMF registrado pero no disponible. No se ha identificado la causa interna de la indisponibilidad de MSMF.

**Corrección:** añadir `cv2.videoio_registry.hasBackend()` a la validación. Si un backend explícito no está disponible, generar `CameraError` con código `backend_unavailable` antes de probar dispositivos. Mantener el backend explícito cuando sí está disponible y no sustituirlo silenciosamente.

**Pruebas:** se añadieron regresiones para descubrimiento/apertura con backend registrado pero no disponible y preservación de un backend explícito disponible. Suite completa ejecutada con `.venv\Scripts\python.exe -m pytest -q`: **44 passed, 1 skipped**. La omisión corresponde a la prueba opcional de cámara física.

Este cambio corrige la validación requerida por la SPEC, sin modificar requisitos ni parámetros aprobados. El usuario confirmó posteriormente el funcionamiento con DSHOW. La indisponibilidad de MSMF se informa explícitamente; INC-00-001 se conserva como limitación conocida aceptada.

### 28.7. INC-00-003 — Estado desactualizado en la barra inferior

**Estado:** CERRADA; corregida y validada en software, con confirmación manual final del usuario.  
**Requisitos relacionados:** RF-00-042 y RNF-00-021 (representación clara de estados).

**Reporte:** el usuario confirmó que volver a DSHOW permite reconocer y utilizar la cámara, pero la barra inferior seguía mostrando «Percepción local · Cámara desconectada» mientras la captura funcionaba.

**Causa:** MainWindow asignaba únicamente un mensaje inicial fijo a QStatusBar, sin observar los cambios de CameraRuntimeState.

**Corrección:** suscribir la barra inferior a CameraController.on_state y representar todos los estados. STREAMING muestra «Percepción local · Cámara conectada · Video en vivo». La actualización conserva los mensajes de cierre/timeout y retira la suscripción al cerrar la ventana.

**Pruebas:** se ampliaron casos de integración existentes para comprobar arranque, conexión, permanencia del estado al navegar, desconexión, error y recuperación. Los casos de shutdown con operaciones bloqueadas mantienen su resultado satisfactorio. Suite completa ejecutada con `.venv\Scripts\python.exe -m pytest -q`: **44 passed, 1 skipped**.

La corrección no modifica requisitos ni políticas aprobadas. El usuario confirmó posteriormente que todo funciona correctamente y solicitó cerrar la SPEC; la validación manual de cámara/frontend se registra como aportada por el usuario. INC-00-001 se conserva como limitación conocida aceptada.

### 28.8. Cierre final y aceptación del usuario

**Fecha de registro:** 6 de octubre de 2026.  
**Estado final:** VALIDATED — terminada y validada en el alcance aceptado por el usuario.  
**Autorización:** solicitud explícita de documentar y dejar SPEC-00 terminada y validada, seguida de confirmación de cierre/reapertura y aceptación expresa de la limitación USB.

**Evidencia de software:** última ejecución de la suite completa, posterior a las correcciones de backend y barra inferior: **44 passed, 1 skipped**. Esta actualización documental no implica una ejecución nueva de tests. La prueba omitida requiere cámara real e índice explícito; la validación física registrada procede de las pruebas manuales del usuario.

**Evidencia de hardware/UI:** cámara real reconocida, conexión y desconexión manual, video y frontend satisfactorios, todos los botones comprobados y cierre con video activo seguido de reapertura y conexión correctas.

**DEC-00-014 — Excepción de cierre para retirada física USB:** el usuario confirma que la recuperación automática con DSHOW todavía falla y acepta el procedimiento manual Desconectar → reconectar USB → Conectar. Para el cierre de SPEC-00, el resultado físico no satisfactorio de TC-00-022 y de los criterios de recuperación automática relacionados se acepta como limitación conocida. Se conserva la trazabilidad con RF-00-046/RF-00-047 y AC-00-008; no se afirma cumplimiento físico de esos comportamientos ni se modifican los resultados de las pruebas.

**Seguimiento no ejecutado:** TC-00-023 no fue ejecutado, según confirmación del usuario. Los FPS, latencia y consumo objetivo siguen TBD; no se inventan mediciones ni se registra el benchmark como aprobado. Tampoco se acredita validación física en Windows 10 y Windows 11 por separado.

**Criterio de cierre:** implementación entregada, pruebas de software registradas, flujo funcional manual con cámara real confirmado y excepción USB aceptada expresamente. El cierre no equivale a ausencia de limitaciones ni a completar las mediciones pendientes. No se inicia automáticamente una SPEC posterior.

---

# Anexo A — Estructura objetivo inicial

```text
blanquita_vision/
│
├── AGENTS.md
├── README.md
├── VISION_INTELIGENTE_BLQ.md
├── ARQUITECTURA_CONEXION.md
├── APP_MOVIL_BLANQ_V2.md
│
├── .python-version
├── .gitignore
├── pyproject.toml
├── uv.lock
├── requirements.txt
│
├── specs/
│   └── SPEC-00_FOUNDATION_ARCHITECTURE_UI_CAPTURE.md
│
├── src/
│   └── blanquita_vision/
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── domain/
│       │   ├── models/
│       │   │   ├── camera_device.py
│       │   │   ├── camera_state.py
│       │   │   ├── capture_configuration.py
│       │   │   └── frame.py
│       │   └── ports/
│       │       └── camera_port.py
│       │
│       ├── application/
│       │   ├── camera_controller.py
│       │   └── latest_frame_store.py
│       │
│       ├── adapters/
│       │   └── camera/
│       │       └── opencv_camera.py
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
│           │   ├── calibration_screen.py
│           │   ├── detection_screen.py
│           │   ├── analytics_screen.py
│           │   ├── reports_screen.py
│           │   ├── diagnostics_screen.py
│           │   └── settings_screen.py
│           ├── workers/
│           │   └── camera_worker.py
│           └── widgets/
│
├── models/
├── calibration/
├── data/
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

Nota:

- Esta estructura puede subdividir archivos internamente durante implementación si no cambia responsabilidades ni crea nuevas carpetas de primer nivel sin justificación.
- `models/`, `calibration/` y `data/` se conservan como parte de la arquitectura global aunque su funcionalidad completa pertenezca a SPECS posteriores.
- `.venv/` existe localmente y no forma parte del árbol versionado.

---

# Anexo B — Baseline tecnológico aplicable a SPEC-00

```text
Windows 10 / Windows 11 x64

Python 3.13.16
uv 0.12.22

UI
PySide6 6.11.2
PyQtGraph 0.14.0

Vision/Capture
NumPy 2.5.3
opencv-contrib-python-headless 4.14.0.94

Testing
pytest 9.1.1
```

Las dependencias de SPECS futuras pueden permanecer declaradas en el baseline global del proyecto, pero SPEC-00 no debe utilizarlas para adelantar funcionalidades.

---

# Anexo C — Decisiones cerradas para SPEC-00

```text
DEC-00-001
Inicio en LIVE sin abrir cámara automáticamente.

DEC-00-002
Navegación mediante sidebar izquierdo.

DEC-00-003
Todos los módulos V1 visibles desde SPEC-00 mediante placeholders cuando aún no estén implementados.

DEC-00-004
Cámaras representadas inicialmente mediante índices: Cámara 0, Cámara 1, etc.

DEC-00-005
Resolución y FPS iniciales negociados/default de la cámara; mostrar valores efectivos.

DEC-00-006
Backend configurable, con AUTO como opción inicial.

DEC-00-007
Backpressure mediante estrategia latest-frame.

DEC-00-008
Desconexión inesperada: recuperación automática limitada; si se agota, ERROR + Reintentar.

DEC-00-009
Captura puntual lógica/efímera en SPEC-00; persistencia en SPEC-02.

DEC-00-010
Ventana inicia maximizada y continúa siendo redimensionable.

DEC-00-011
Diseño principal del frontend en negro, técnico y de alto contraste.

DEC-00-012
Se utiliza .venv para el entorno virtual local.

DEC-00-013
Se incorpora requirements.txt como export de compatibilidad, sin desplazar pyproject.toml + uv.lock como fuente de verdad.

DEC-00-014
Cierre de SPEC-00 autorizado con la limitación conocida de retirada USB con DSHOW;
se acepta recuperación manual mediante Desconectar, reconectar USB y Conectar.
TC-00-022 permanece fallido; no se declara corregida la recuperación automática.
```

---

# Revisión de completitud de SPEC-00

```text
✓ Requisitos funcionales definidos
✓ Requisitos no funcionales definidos
✓ Casos de uso definidos
✓ Estados definidos
✓ Modelos de datos base definidos
✓ CameraPort definido conceptualmente
✓ OpenCvCamera definido como adapter
✓ Concurrencia definida
✓ latest-frame definido
✓ Errores principales definidos
✓ UI/UX definida
✓ Tema negro confirmado
✓ .venv considerado
✓ requirements.txt considerado
✓ Persistencia fuera de alcance correctamente delimitada
✓ Tests automatizables definidos
✓ Tests hardware distinguidos
✓ Criterios de aceptación definidos
✓ Definition of Done definida
✓ Dependencias entre SPECS definidas
✓ Riesgos definidos
✓ Trazabilidad definida
✓ No se adelanta calibración
✓ No se adelanta detección
✓ No se adelanta posición X/Y/Z
✓ No se adelanta WebSocket
✓ No se adelanta SQLite
✓ No se adelanta ONNX
✓ No se traslada autoridad del móvil a la laptop
✓ No se inventan métricas de rendimiento
✓ Decisiones numéricas aún no sustentadas quedan abiertas
```

---

# Estado final del documento

```text
SPEC-00
Fundación, arquitectura, UI y captura

ESTADO:
VALIDATED

CIERRE:
SPEC-00 terminada y validada por aceptación explícita del usuario,
con la limitación USB y el benchmark no ejecutado registrados en 28.8.

Implementación y validación de software completadas; flujo funcional
manual con cámara real y cierre/reapertura confirmados por el usuario.
No avanzar automáticamente a la siguiente SPEC.
```

## Decisiones complementarias aprobadas para implementación

- Tres lecturas inválidas consecutivas durante streaming inician recuperación. Un primer frame inválido durante conexión produce ERROR.
- Cancelación desde DISCOVERING, CONNECTING o RECOVERING: STOPPING → DISCONNECTED.
- Actualizar cámaras desde ERROR: DISCOVERING → DISCONNECTED.
- El cierre cancela operaciones y espera asíncronamente hasta cinco segundos. Si el worker sigue bloqueado, la ventana permanece abierta con un error explícito; no se termina forzosamente el hilo. Al concluir el worker, puede completarse el cierre.
- Los tiempos y límites anteriores son parámetros iniciales aprobados, no resultados de benchmark ni validación de hardware.
