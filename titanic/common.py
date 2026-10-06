"""Small helpers shared by this film's modules."""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, filename):
    """Import a module from this folder by path (src/ has modules with the same names)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_narration(lang):
    return load(f"titanic_narration_{lang}",
                "narration.py" if lang == "en" else f"narration_{lang}.py").SEGMENTS
