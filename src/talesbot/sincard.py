import logging

from pydantic import ConfigDict, TypeAdapter

from talesbot.config import config_dir

logger = logging.getLogger(__name__)

sincard_model = TypeAdapter(dict[str, str], config=ConfigDict(strict=True))


def load_sincard_config() -> dict[str, str]:
    path = config_dir / "sincards.json"
    try:
        with open(path) as f:
            return sincard_model.validate_json(f.read())
    except Exception:
        logger.error("Failed to open sincard config", exc_info=True)
        return {}


def map_handle(handle: str | None) -> str | None:
    if handle is None:
        return None
    data = load_sincard_config()
    return data.get(handle, handle)
