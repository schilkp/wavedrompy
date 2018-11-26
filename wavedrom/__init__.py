import json

from .wavedrom import WaveDrom
from .assign import Assign
from .version import version


def render(index=0, source="", output=[]):
    source = json.loads(source)
    if source.get("signal"):
        return WaveDrom().renderWaveForm(index, source, output)
    elif source.get("assign"):
        return Assign().render(index, source, output)