# BLANQUITA MOBILE V2 — Arquitectura, módulos y responsabilidades

## 1. Propósito del documento

Este documento define la arquitectura funcional y técnica de **BLANQUITA Mobile V2**, la aplicación móvil principal del proyecto BLANQUITA.

La aplicación móvil será el **centro de supervisión, decisión y control** del robot cartesiano.

La arquitectura general del sistema se basa en tres responsabilidades claramente separadas:

```text
LAPTOP
PERCEPCIÓN
      ↓
MÓVIL
DECISIÓN + SUPERVISIÓN
      ↓
ESP32
EJECUCIÓN + PROTECCIÓN
```

La aplicación móvil no realizará procesamiento pesado de visión artificial.

El procesamiento de cámara, detección, calibración y análisis visual se ejecutará en un programa independiente instalado en una laptop.

BLANQUITA Mobile recibirá los resultados del visor inteligente, los mostrará al usuario y, cuando corresponda, validará si una acción automatizada puede convertirse en una orden física hacia el ESP32.

---

# 2. Rol de BLANQUITA Mobile

BLANQUITA Mobile será la **única autoridad de control de alto nivel** del sistema.

Sus principales responsabilidades serán:

- Supervisar el estado general del robot.
- Controlar manualmente el cartesiano.
- Enviar comandos al ESP32.
- Recibir estados y eventos del ESP32.
- Recibir reportes del visor inteligente.
- Mostrar los resultados visuales recibidos desde la laptop.
- Validar acciones automatizadas.
- Coordinar visión y movimiento.
- Ejecutar STOP y emergencia.
- Mostrar diagnósticos.
- Persistir configuraciones.
- Registrar reportes y eventos relevantes.
- Mantener operación manual aunque falle la laptop.

La laptop no debe controlar directamente al ESP32.

El flujo correcto será:

```text
Laptop
   │
   │ VisionReport
   ▼
BLANQUITA Mobile
   │
   │ validación / decisión
   ▼
ESP32
   │
   ▼
Robot cartesiano
```

---

# 3. Arquitectura de comunicación

La aplicación móvil tendrá dos conexiones WebSocket independientes.

```text
                    BLANQUITA MOBILE
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
        ESP32 CONTROL                LAPTOP VISION
        WebSocket                    WebSocket
```

## 3.1. WebSocket con ESP32

Canal utilizado para:

- Movimiento.
- STOP.
- Emergencia.
- Heartbeat.
- Pinza.
- Velocidad.
- Secuencia automática.
- Sensores.
- Estados.
- Errores.

Conceptualmente:

```text
BLANQUITA MOBILE
       ⇅
   WebSocket
       ⇅
      ESP32
```

---

## 3.2. WebSocket con laptop

Canal utilizado para:

- Reportes de visión.
- Estado de cámara.
- Estado del detector.
- Estado de calibración.
- Posición estimada.
- Confianza.
- Alertas.
- Heartbeat del visor.
- Errores del visor.

Conceptualmente:

```text
BLANQUITA MOBILE
       ⇅
   WebSocket
       ⇅
BLANQUITA VISION
```

---

# 4. Principio de autoridad

Aunque todos los dispositivos se encuentren en la misma red local, no todos tendrán permiso de control físico.

La aplicación móvil será la única autoridad de control de alto nivel.

```text
Laptop
   │
   └── informa

Móvil
   │
   └── decide y controla

ESP32
   │
   └── ejecuta y protege
```

La laptop no enviará comandos crudos al ESP32.

Ejemplo NO recomendado:

```json
{
  "command": "d"
}
```

Ejemplo recomendado:

```json
{
  "type": "object_position",
  "x": 145.2,
  "z": 78.4,
  "confidence": 0.96
}
```

La aplicación móvil será responsable de convertir información de alto nivel en acciones físicas cuando corresponda.

---

# 5. Stack tecnológico móvil

Se mantendrá el stack principal actual de BLANQUITA.

## 5.1. Framework

```text
Flutter
```

## 5.2. Lenguaje

```text
Dart
```

## 5.3. Gestión de estado

```text
Provider
ChangeNotifier
```

No se recomienda migrar a BLoC, Riverpod u otro gestor solamente por la evolución del proyecto.

---

## 5.4. Comunicación

```text
web_socket_channel
```

Se utilizará para:

- ESP32.
- Laptop Vision Server.

---

## 5.5. Persistencia de configuración

```text
SharedPreferences
```

Utilizado para:

- IP/URL ESP32.
- IP/URL laptop.
- preferencias de interfaz;
- preferencias de seguridad;
- modo de operación;
- configuraciones generales.

---

## 5.6. Persistencia de reportes

Para almacenar históricos de reportes, eventos y automatizaciones se recomienda:

```text
SQLite
+
Drift
```

SharedPreferences no debe utilizarse como almacenamiento de historial.

---

## 5.7. Serialización

Para mensajes estructurados Laptop ↔ Mobile se recomienda:

```text
json_annotation
json_serializable
build_runner
```

Esto permitirá tener modelos fuertemente tipados.

---

## 5.8. Testing

```text
flutter_test
integration_test
```

---

# 6. Patrón arquitectónico

La aplicación mantendrá una arquitectura:

> **Feature-first + presentación reactiva + controladores ChangeNotifier, similar a MVVM ligero.**

No se implementará Clean Architecture estricta si no existe una necesidad real.

Sin embargo, se mejorará la separación actual entre:

```text
UI
↓
Controller
↓
Service
↓
Transport
```

Arquitectura objetivo:

```text
PRESENTATION
     │
     ▼
CONTROLLERS
     │
     ▼
DOMAIN
     │
     ▼
SERVICES
     │
     ▼
TRANSPORTS
     │
     ▼
WEBSOCKET / STORAGE
```

---

# 7. Estructura general de módulos

BLANQUITA Mobile se organizará funcionalmente en los siguientes módulos:

```text
Dashboard

Machine

Control

Vision

Automation

Safety

Reports

Diagnostics

Settings

Core / Infrastructure
```

---

# 8. Módulo Dashboard

El Dashboard será el centro principal de supervisión.

Debe mostrar:

```text
Estado ESP32

Estado laptop

Estado visor

Estado cámara

Estado calibración

Estado detector

Modo de operación

Movimiento actual

Pinza

Sensores

Última detección

Confianza

Posición X/Z

Alertas

Últimos eventos
```

Ejemplo conceptual:

```text
BLANQUITA
────────────────────────

ESP32
● CONECTADO

VISOR INTELIGENTE
● CONECTADO

CÁMARA
● OPERATIVA

CALIBRACIÓN
● VÁLIDA

MODO
ASISTIDO

ROBOT
DETENIDO

OBJETO
PIEZA

X: 145.2 mm
Z: 78.4 mm
Confianza: 96 %
```

---

# 9. Módulo Machine

Este módulo representará el estado operativo del robot.

## Responsabilidades

- Estado de conexión ESP32.
- Movimiento actual.
- Estado de pinza.
- Estado de secuencia.
- Sensores.
- Último RX.
- Último TX.
- Eventos.
- Estado de disponibilidad.
- Reconexión.

Arquitectura:

```text
MachineController
       │
       ▼
MachineService
       │
       ▼
Esp32Transport
       │
       ▼
WebSocket
```

---

# 10. MachineController

El controlador actual deberá evolucionar para concentrarse en la lógica de coordinación y no en todos los detalles de transporte.

Responsabilidades recomendadas:

```text
coordinar estados

validar reglas simples de máquina

manejar acciones de usuario

recibir eventos del MachineService

exponer estado a UI
```

No debería crear directamente el WebSocket a largo plazo.

---

# 11. Esp32Transport

Se recomienda introducir una abstracción para el transporte.

Conceptualmente:

```dart
abstract interface class Esp32Transport {
  Stream<String> get messages;

  Future<void> connect(Uri uri);

  Future<void> disconnect();

  Future<void> send(String message);
}
```

Implementación:

```text
WebSocketEsp32Transport
```

Ventajas:

- Testing.
- Simulación.
- Desacoplamiento.
- Posibilidad de cambiar transporte en el futuro.

---

# 12. Módulo Control

Debe mantener todas las capacidades actuales.

## Control manual

```text
Mover X izquierda

Mover X derecha

Mover Z arriba

Mover Z abajo
```

Debe conservar la interacción `hold-to-move`.

---

## Pinza

```text
Abrir

Cerrar
```

---

## Velocidad

```text
Aumentar

Disminuir
```

---

## STOP

Debe estar disponible siempre que exista comunicación con el ESP32.

---

## Emergencia

Debe tener prioridad sobre cualquier otra operación.

---

## Secuencia automática

La secuencia convencional del ESP32 debe mantenerse separada de la futura automatización basada en visión.

---

# 13. Protocolo ESP32

Se mantendrá el protocolo actual durante la primera evolución de BLANQUITA Mobile.

```text
a = mover izquierda

d = mover derecha

w = subir Z

s = bajar Z

x = STOP

k = heartbeat

q = abrir pinza

e = cerrar pinza

j = secuencia automática

z = emergencia

+ = aumentar velocidad

- = disminuir velocidad
```

---

# 14. Módulo Vision

La aplicación móvil no realizará captura ni procesamiento de cámara.

Su módulo Vision será un cliente remoto del visor inteligente.

Arquitectura:

```text
Laptop
   │
   │ WebSocket
   ▼
RemoteVisionService
   │
   ▼
VisionController
   │
   ▼
VisionScreen
```

---

# 15. VisionController

Responsabilidades:

- Conectarse al Vision Server.
- Recibir mensajes.
- Parsear reportes.
- Mantener el estado del visor.
- Detectar pérdida de conexión.
- Detectar reportes caducados.
- Exponer información a la UI.
- Enviar eventos al AutomationCoordinator.

Estado conceptual:

```text
VisionState
├── connection
├── cameraStatus
├── detectorStatus
├── calibrationStatus
├── lastReport
├── lastHeartbeat
├── error
└── latency
```

---

# 16. VisionScreen

La pantalla Visión será un monitor del sistema remoto.

Debe mostrar:

```text
Estado laptop

Estado WebSocket

Estado cámara

Nombre de cámara

Estado calibración

Estado detector

FPS

Último reporte

Objeto detectado

Posición X

Posición Z

Confianza

Edad del reporte

Alertas
```

Ejemplo:

```text
VISOR INTELIGENTE
────────────────────────

Laptop
● Conectada

Cámara
CMSXJ22A
● Operativa

Calibración
● Válida

Detector
● Activo

Objeto:
PIEZA

X:
145.2 mm

Z:
78.4 mm

Confianza:
96 %

Última actualización:
18:32:14
```

En V1 no es obligatorio transmitir video en tiempo real al celular.

---

# 17. Modelos de visión

Se recomienda definir modelos claros.

## PositionEstimate

```text
x

z

confidence

timestamp
```

---

## VisionReport

Puede contener:

```text
id

timestamp

detected

object

position

confidence

cameraStatus

calibrationStatus

detectorStatus

alerts
```

---

## VisionStatus

```text
connected

ready

fps

cameraConnected

calibrated

detectorRunning

lastHeartbeat
```

---

# 18. Protocolo Laptop ↔ Mobile

La comunicación debe utilizar JSON versionado.

Ejemplo:

```json
{
  "protocol": "blanquita-vision",
  "version": 1,
  "type": "vision.report",
  "messageId": "UUID",
  "timestamp": "2026-10-05T18:32:14",
  "payload": {
    "detected": true,
    "object": "pieza",
    "position": {
      "x": 145.2,
      "z": 78.4
    },
    "confidence": 0.96
  }
}
```

---

# 19. Tipos de mensajes de visión

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

Estos mensajes únicamente controlan el subsistema de visión.

No autorizan a la laptop a mover el robot.

---

# 20. Heartbeat de visión

El móvil debe detectar si el Vision Server desaparece.

Conceptualmente:

```text
Laptop
   │
   ├── heartbeat
   ├── heartbeat
   ├── heartbeat
   │
   X

Móvil
   ↓
VISION_STALE
   ↓
Automatización deshabilitada
```

La pérdida de visión NO debe desconectar el control manual del ESP32.

---

# 21. Módulo Automation

Se creará un módulo específico para automatización.

Componente principal:

```text
AutomationCoordinator
```

Responsabilidad:

```text
combinar resultados de visión

estado de máquina

modo operativo

reglas de seguridad

decidir si una acción puede ejecutarse
```

Arquitectura:

```text
VisionState
    │
    ▼
AutomationCoordinator
    ▲
    │
MachineState
    │
    ▼
SafetyGate
    │
    ▼
MachineController
    │
    ▼
ESP32
```

---

# 22. Modos de operación

Se recomiendan tres modos.

## 22.1. Manual

```text
Usuario
   ↓
Móvil
   ↓
ESP32
```

La visión puede estar activa, pero no genera acciones.

---

## 22.2. Asistido

```text
Laptop detecta
      ↓
Móvil recibe
      ↓
Móvil muestra sugerencia
      ↓
Usuario confirma
      ↓
Móvil ejecuta
```

Este modo será especialmente importante durante desarrollo y pruebas.

---

## 22.3. Automático

```text
Laptop detecta
      ↓
Móvil recibe
      ↓
AutomationCoordinator
      ↓
SafetyGate
      ↓
MachineController
      ↓
ESP32
```

Este modo debe implementarse solamente cuando las validaciones estén suficientemente maduras.

---

# 23. Módulo Safety

Se recomienda introducir:

```text
SafetyGate
```

Su responsabilidad es centralizar validaciones antes de ejecutar acciones automatizadas.

Ejemplo:

```text
¿ESP32 conectado?

¿Laptop conectada?

¿VisionReport reciente?

¿Calibración válida?

¿Confianza suficiente?

¿Sin emergencia?

¿Final de carrera libre?

¿Sin secuencia activa?

¿Máquina disponible?

¿Modo automático habilitado?
```

---

# 24. Respuestas del SafetyGate

Ejemplos:

```text
ACCEPTED
```

o:

```text
REJECTED
VISION_REPORT_STALE
```

Otros posibles motivos:

```text
ESP32_DISCONNECTED

VISION_DISCONNECTED

LOW_CONFIDENCE

CALIBRATION_INVALID

LIMIT_SWITCH_ACTIVE

SEQUENCE_ACTIVE

EMERGENCY_ACTIVE

MACHINE_BUSY

AUTOMATIC_MODE_DISABLED
```

Esto facilita diagnóstico y auditoría.

---

# 25. Seguridad operacional

La app móvil debe agregar validaciones, pero no reemplazar las protecciones del ESP32.

Principio:

```text
Móvil valida

ESP32 protege
```

El ESP32 debe conservar:

```text
final de carrera

timeout

watchdog

STOP

emergencia
```

---

# 26. Comportamiento ante pérdida de laptop

Si el Vision Server se desconecta:

```text
Visión inteligente       OFF

Automatización visión    OFF

Control manual           ON

STOP                     ON

Emergencia               ON

ESP32                    ON
```

La laptop no debe ser una dependencia para el control manual.

---

# 27. Comportamiento ante pérdida del ESP32

Si se pierde el ESP32:

```text
Control manual          DESHABILITADO

Automatización          DESHABILITADA

Secuencia               DESHABILITADA

STOP                    no transmisible

Visión                  puede continuar
```

La UI debe mostrar claramente:

```text
ESP32 DESCONECTADO
```

---

# 28. Comportamiento ante pérdida del móvil

Si la aplicación desaparece durante movimiento manual, el ESP32 debe detenerse mediante heartbeat/timeout.

La seguridad física no debe depender únicamente de Flutter.

---

# 29. Módulo Reports

Se recomienda registrar reportes relevantes localmente.

Un registro puede contener:

```text
id

timestamp

tipo de objeto

posición X

posición Z

confidence

estado de calibración

modo

decisión

acción

resultado

alertas
```

Ejemplo:

```text
Reporte #000142

Fecha:
05/10/2026

Hora:
18:32:14

Objeto:
PIEZA

X:
145.2 mm

Z:
78.4 mm

Confianza:
96 %

Modo:
ASISTIDO

Decisión:
ACEPTADA

Acción:
MOVIMIENTO

Resultado:
COMPLETADO
```

---

# 30. Persistencia de reportes

No utilizar SharedPreferences.

Se recomienda:

```text
Drift
+
SQLite
```

Tablas futuras posibles:

```text
vision_reports

automation_events

system_events
```

---

# 31. Módulo Diagnostics

Debe centralizar información de ambos canales.

## ESP32

```text
endpoint

estado

último RX

último TX

READY

último error

reconexiones

heartbeat
```

## Laptop

```text
endpoint

estado

último reporte

último heartbeat

último error

latencia

estado cámara

estado detector

calibración
```

---

# 32. Módulo Settings

Se recomienda dividir ajustes en:

```text
CONEXIÓN ESP32

CONEXIÓN VISIÓN

CONTROL

AUTOMATIZACIÓN

SEGURIDAD

APARIENCIA

DIAGNÓSTICOS
```

---

## 32.1. ESP32

```text
URL / IP

puerto

auto-reconnect

timeout
```

---

## 32.2. Visión

```text
URL / IP laptop

puerto

auto-reconnect

timeout heartbeat

confidence mínima
```

---

## 32.3. Automatización

```text
modo

confirmación humana

confidence mínima

edad máxima de reporte
```

---

# 33. Persistencia de ajustes

Seguir utilizando:

```text
SettingsRepository

SettingsController

SharedPreferences
```

No crear un sistema paralelo de configuración.

---

# 34. Estructura de carpetas propuesta

```text
lib/
│
├── main.dart
│
├── app/
│   ├── app.dart
│   ├── navigation/
│   └── theme/
│
├── core/
│   ├── network/
│   │   ├── websocket_client.dart
│   │   ├── connection_state.dart
│   │   └── network_error.dart
│   │
│   ├── storage/
│   ├── protocol/
│   ├── haptics/
│   └── errors/
│
├── features/
│
│   ├── machine/
│   │   ├── domain/
│   │   │   ├── machine_state.dart
│   │   │   └── machine_command.dart
│   │   ├── services/
│   │   │   └── machine_service.dart
│   │   ├── controller/
│   │   │   └── machine_controller.dart
│   │   └── presentation/
│
│   ├── control/
│   │   └── presentation/
│
│   ├── dashboard/
│
│   ├── vision/
│   │   ├── domain/
│   │   │   ├── vision_report.dart
│   │   │   ├── vision_state.dart
│   │   │   ├── vision_status.dart
│   │   │   └── position_estimate.dart
│   │   ├── services/
│   │   │   └── remote_vision_service.dart
│   │   ├── controller/
│   │   │   └── vision_controller.dart
│   │   └── presentation/
│
│   ├── automation/
│   │   ├── automation_coordinator.dart
│   │   ├── automation_mode.dart
│   │   └── safety_gate.dart
│
│   ├── reports/
│   │   ├── domain/
│   │   ├── repository/
│   │   └── presentation/
│
│   ├── diagnostics/
│   └── settings/
│
└── shared/
    └── widgets/
```

---

# 35. Dependencias recomendadas

## Mantener

```text
provider

shared_preferences

web_socket_channel

cupertino_icons

flutter_test

flutter_lints
```

---

## Añadir cuando se implemente protocolo Vision

```text
json_annotation

json_serializable

build_runner
```

---

## Añadir cuando se implemente historial

```text
drift

sqlite3_flutter_libs

path_provider

path
```

Las versiones exactas deben definirse cuando se realice la implementación y validarse contra la versión actual de Flutter/Dart.

---

# 36. Librerías que NO son necesarias en Mobile

No introducir inicialmente:

```text
OpenCV

PyTorch

TensorFlow

YOLO

camera

UVC

MediaPipe
```

El móvil no será el procesador del visor inteligente.

---

# 37. Testing recomendado

La aplicación necesita pruebas especialmente en:

```text
MachineController

VisionController

AutomationCoordinator

SafetyGate

protocol parser

reconexión

heartbeat

reportes

persistencia
```

---

# 38. Fake transports

Se recomienda poder sustituir:

```text
ESP32 real
```

por:

```text
FakeEsp32Transport
```

y:

```text
Laptop real
```

por:

```text
FakeVisionTransport
```

Esto permite probar:

```text
READY

desconexión

error

reporte válido

reporte antiguo

confidence baja

final de carrera

emergencia

secuencia activa
```

sin hardware.

---

# 39. Pruebas de integración

Se deberán probar escenarios como:

```text
App conecta con ESP32

ESP32 envía READY

App conecta con laptop

Laptop envía vision.ready

Laptop envía vision.report

Móvil valida

SafetyGate acepta

MachineController envía comando

ESP32 confirma
```

---

# 40. Reconexión

Cada conexión debe manejarse independientemente.

```text
MachineConnection
```

puede estar:

```text
CONNECTED
```

mientras:

```text
VisionConnection
```

está:

```text
DISCONNECTED
```

y viceversa.

La pérdida de una conexión no debe destruir la otra.

---

# 41. Estados globales

Conceptualmente el sistema móvil manejará:

```text
MachineState

VisionState

AutomationState

SettingsState
```

La UI combinará esos estados cuando sea necesario.

---

# 42. Automatización basada en eventos

No se recomienda que VisionController ordene directamente movimientos.

Incorrecto:

```text
VisionController
       ↓
MachineController
```

Preferido:

```text
VisionController
       ↓
AutomationCoordinator
       ↓
SafetyGate
       ↓
MachineController
```

Esto mantiene separación de responsabilidades.

---

# 43. Flujo de automatización completo

```text
Laptop
   │
   ▼
vision.report
   │
   ▼
RemoteVisionService
   │
   ▼
VisionController
   │
   ▼
VisionState
   │
   ▼
AutomationCoordinator
   │
   ▼
SafetyGate
   │
   ├── REJECTED
   │
   └── ACCEPTED
           │
           ▼
    MachineController
           │
           ▼
       MachineService
           │
           ▼
      Esp32Transport
           │
           ▼
         ESP32
```

---

# 44. Flujo manual

El control manual debe permanecer simple.

```text
Usuario
   │
   ▼
ControlScreen
   │
   ▼
MachineController
   │
   ▼
ESP32
```

No debe depender del visor.

---

# 45. Filosofía de degradación

El sistema debe degradarse por funciones.

```text
Laptop caída
→ pierdo visión

ESP32 caído
→ pierdo control físico

Móvil activo
→ puedo diagnosticar

Visión caída
→ manual continúa
```

La pérdida del visor no debe convertirse en pérdida total del robot.

---

# 46. UX recomendada

La app debe indicar claramente:

```text
CONTROL MANUAL DISPONIBLE

VISIÓN DESCONECTADA
```

en lugar de bloquear todo el sistema por una falla secundaria.

---

# 47. Indicadores visuales

Se recomienda utilizar estados consistentes:

```text
● Verde = operativo

● Amarillo = degradado / pendiente

● Rojo = error / bloqueo

● Gris = no disponible
```

---

# 48. Notificaciones importantes

Ejemplos:

```text
ESP32 desconectado

Visor desconectado

Reporte de visión caducado

Calibración inválida

Confianza insuficiente

Final de carrera activo

Movimiento bloqueado

Secuencia activa

Emergencia activada
```

---

# 49. Restricciones de diseño

BLANQUITA Mobile no debe:

- Procesar visión pesada.
- Acceder directamente a la webcam USB.
- Ejecutar modelos ML pesados.
- Permitir que la laptop controle directamente el robot.
- Mezclar lógica de visión dentro de MachineController.
- Hacer depender el control manual de la laptop.
- Considerar Wi-Fi conectado como equivalente a ESP32 conectado.
- Ejecutar automatizaciones con reportes antiguos.
- Ejecutar automatizaciones sin validar seguridad.

---

# 50. Evolución futura

En versiones posteriores se podría añadir:

```text
descubrimiento automático de dispositivos

mDNS

múltiples ESP32

múltiples observadores

streaming opcional

sincronización avanzada

perfiles de automatización

exportación de reportes

auditoría

historial avanzado
```

Sin cambiar la separación principal:

```text
Laptop
Percepción

Móvil
Decisión

ESP32
Ejecución
```

---

# 51. Resumen final

BLANQUITA Mobile V2 será una aplicación Flutter responsable de:

```text
SUPERVISIÓN

CONTROL MANUAL

DECISIÓN

VALIDACIÓN

AUTOMATIZACIÓN

SEGURIDAD LÓGICA

REPORTES

DIAGNÓSTICOS
```

Mantendrá dos conexiones principales:

```text
Móvil ⇄ ESP32

Móvil ⇄ Laptop
```

La arquitectura interna se organizará mediante:

```text
UI

Controllers

Domain

Services

Transports

Storage
```

La lógica futura de automatización utilizará:

```text
VisionController
       ↓
AutomationCoordinator
       ↓
SafetyGate
       ↓
MachineController
       ↓
ESP32
```

El principio rector será:

> **La laptop percibe, la app móvil decide y supervisa, y el ESP32 ejecuta y protege.**

BLANQUITA Mobile debe continuar siendo completamente utilizable en modo manual aun cuando la laptop o el visor inteligente no estén disponibles.
