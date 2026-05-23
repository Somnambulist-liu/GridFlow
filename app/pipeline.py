"""Feature pipeline — share output files between features."""
from PySide6.QtCore import QObject, Signal


class PipelineContext(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._outputs: dict[str, str] = {}

    def set_output(self, feature_id: str, file_path: str):
        self._outputs[feature_id] = file_path
        self.changed.emit()

    def get_output(self, feature_id: str) -> str | None:
        return self._outputs.get(feature_id)

    def all_outputs(self) -> dict[str, str]:
        return dict(self._outputs)

    def clear(self):
        self._outputs.clear()
        self.changed.emit()

    @property
    def has_outputs(self) -> bool:
        return len(self._outputs) > 0
