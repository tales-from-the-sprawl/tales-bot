from pydantic import ConfigDict, TypeAdapter

from talesbot.config import config_dir

sincard_model = TypeAdapter(dict[str, str], config=ConfigDict(strict=True))


def load_sincard_config() -> dict[str, str]:
    path = config_dir / "sincards.json"
    with open(path) as f:
        return sincard_model.validate_json(f.read())


def map_handle(handle: str | None) -> str | None:
    if handle is None:
        return None
    data = load_sincard_config()
    return data.get(handle, handle)
