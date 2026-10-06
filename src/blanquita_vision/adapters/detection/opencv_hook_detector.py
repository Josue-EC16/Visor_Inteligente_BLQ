from time import perf_counter

import cv2
import numpy as np

from ...domain.models.detection import Detection, DetectionCandidate, DetectionParameters
from ...domain.models.frame import Frame
from ...domain.models.geometry import BoundingBox, ImagePoint


class OpenCvHookDetector:
    """Quality score = solidez × ocupación; no es probabilidad estadística."""

    def __init__(self) -> None:
        self.candidates: tuple[DetectionCandidate, ...] = ()
        self.last_timings: tuple[float, float] = (0.0, 0.0)

    def detect(self, frame: Frame, parameters: DetectionParameters) -> Detection:
        started = perf_counter()
        image = np.asarray(frame.image)
        if image.dtype != np.uint8 or image.shape[:2] != (frame.height, frame.width):
            raise ValueError("Formato o dimensiones del frame incompatibles.")
        if image.ndim != 3 or image.shape[2] not in (3, 4):
            raise ValueError("La detección de color requiere una imagen BGR/BGRA.")
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            (parameters.hue_min, parameters.saturation_min, parameters.value_min),
            (parameters.hue_max, parameters.saturation_max, parameters.value_max),
        )
        if parameters.morphology_enabled:
            size = parameters.morphology_kernel_size
            if size > min(frame.width, frame.height):
                raise ValueError("El kernel morfológico no debe superar las dimensiones del frame.")
            kernel = np.ones((size, size), dtype=np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        preprocessed = perf_counter()
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area <= 0 or area < parameters.min_area:
                continue
            if parameters.max_area is not None and area > parameters.max_area:
                continue
            x, y, width, height = cv2.boundingRect(contour)
            hull_area = float(cv2.contourArea(cv2.convexHull(contour)))
            solidity = min(1.0, max(0.0, area / hull_area)) if hull_area > 0 else 0.0
            # Medir únicamente esta componente, sin sumar otros contornos interiores.
            component = np.zeros((height, width), dtype=np.uint8)
            shifted = contour - np.asarray([[[x, y]]], dtype=contour.dtype)
            cv2.drawContours(component, [shifted], -1, 255, thickness=cv2.FILLED)
            color_pixels = cv2.countNonZero(cv2.bitwise_and(mask[y:y + height, x:x + width], component))
            coverage = color_pixels / (width * height)
            score = min(1.0, max(0.0, solidity * coverage))
            if score < parameters.minimum_confidence:
                continue
            moments = cv2.moments(contour)
            box = BoundingBox(x, y, width, height)
            centroid = ImagePoint(moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
            candidates.append(DetectionCandidate(box, centroid, area, coverage, solidity, score))
        candidates.sort(key=lambda candidate: candidate.confidence, reverse=True)
        self.candidates = tuple(candidates)
        ambiguous = len(candidates) > 1 and candidates[0].confidence == candidates[1].confidence
        self.last_timings = ((preprocessed - started) * 1000,
                             (perf_counter() - preprocessed) * 1000)
        if not candidates or ambiguous:
            return Detection(False, "gancho", None, None, 0.0,
                             frame.captured_at, frame.sequence, ambiguous)
        chosen = candidates[0]
        return Detection(True, "gancho", chosen.bounding_box, chosen.centroid,
                         chosen.confidence, frame.captured_at, frame.sequence)
