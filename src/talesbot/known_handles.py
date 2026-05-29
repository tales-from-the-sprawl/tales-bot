import csv
import logging
from typing import Annotated, Any

from annotated_types import T
from pydantic import BaseModel, BeforeValidator, Field, ValidationError

from talesbot.config import config_dir

logger = logging.getLogger(__name__)


known_handle_file = config_dir / "known_handles.csv"


def _parse_list(value: Any) -> Any:
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        if value.strip() == "":
            return []
        return [v.strip() for v in value.split(",") if v.strip() != ""]
    else:
        raise ValueError("Input should be csv string")


def _parse_keyval(value: Any) -> Any:
    if isinstance(value, list):
        return {
            k: v for k, v in map(lambda x: (y.strip() for y in x.split(":")), value)
        }
    else:
        raise ValueError("Input should be csv keyval")


def _parse_x_bool(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip() == "x"
    elif isinstance(value, bool):
        return value
    else:
        raise ValueError("Input should be x bool")


def _parse_empty_string(value: Any) -> Any:
    if value == "":
        return 0
    else:
        return value


CsvDict = Annotated[
    dict[str, T],
    BeforeValidator(_parse_keyval),
    BeforeValidator(_parse_list),
]
CsvList = Annotated[list[T], BeforeValidator(_parse_list)]
XBool = Annotated[bool, BeforeValidator(_parse_x_bool)]
EmptyStrZero = Annotated[T, BeforeValidator(_parse_empty_string)]


class KnownHandle(BaseModel):
    name: str = Field(validation_alias="Spelare")
    role_name: str = Field(validation_alias="Rollnamn")
    handle: str = Field(validation_alias="Main handle")
    balance: EmptyStrZero[int] = Field(validation_alias="Pengar på main:", default=0)
    alt_handles: CsvList[str] = Field(validation_alias="Alternativa handles")
    alt_balance: CsvDict[int] = Field(validation_alias="Pengar på övriga:")
    groups: CsvList[str] = Field(validation_alias="Grupper:")
    tacoma: XBool = Field(validation_alias="Tacoma", default=False)
    actor_id: str | None = Field(validation_alias="u-nummer")
    server: str | None = Field(validation_alias="Server")
    category: str | None = Field(validation_alias="Category")


def read_known_handles() -> dict[str, KnownHandle]:
    with open(known_handle_file) as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        handles = []
        for row in reader:
            try:
                handles.append(KnownHandle.model_validate(row, strict=False))
            except ValidationError:
                logger.exception(f"error reading known handle {row}")

        return {h.handle: h for h in handles}
