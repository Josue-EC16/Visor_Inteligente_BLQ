from ..domain.models.calibration import CalibrationStatus
from ..domain.models.detection import DetectionState
from ..domain.models.tracking import TrackingState
from ..domain.models.vision_observation import VisionPipelineState

PIPELINE_TEXT = {
    VisionPipelineState.STOPPED: "Detenido", VisionPipelineState.STARTING: "Iniciando",
    VisionPipelineState.RUNNING: "Activo", VisionPipelineState.STOPPING: "Deteniendo",
    VisionPipelineState.ERROR: "Error",
}
CALIBRATION_TEXT = {
    CalibrationStatus.UNCALIBRATED: "Sin calibrar", CalibrationStatus.CALIBRATING: "Marcando / calculando",
    CalibrationStatus.VALID: "Válida", CalibrationStatus.INVALID: "Inválida", CalibrationStatus.ERROR: "Error",
}
DETECTION_TEXT = {
    DetectionState.DISABLED: "Desactivado", DetectionState.SEARCHING: "Buscando / ambiguo",
    DetectionState.DETECTED: "Detectado", DetectionState.NOT_DETECTED: "Buscando: no detectado",
    DetectionState.ERROR: "Error",
}
TRACKING_TEXT = {
    TrackingState.INACTIVE: "Inactivo", TrackingState.INITIALIZING: "Inicializando",
    TrackingState.TRACKING: "Siguiendo", TrackingState.LOST: "Perdido", TrackingState.ERROR: "Error",
}


def position_text(estimate) -> str:
    if estimate is None:
        return "X/Y físicos: No disponibles · Z: No disponible"
    raw, filtered = estimate.raw_position, estimate.filtered_position
    return (f"Raw: X={raw.x:.3f}, Y={raw.y:.3f} {raw.unit} · "
            f"Filtrada: X={filtered.x:.3f}, Y={filtered.y:.3f} {filtered.unit} · Z: No disponible")


def milliseconds(value) -> str:
    return "No disponible" if value is None else f"{value:.2f} ms"
