# module scenarios.py

# This module handles the creation and execution of scenarios, which are automated sequences of in-game events.
# A scenario could be for example a simulated network crash, automated spam messages, or creation of a new group.

import abc
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum, StrEnum
from typing import override

from configobj import ConfigObj
from discord.abc import GuildChannel
from pydantic import BaseModel, Field

from . import game, groups, players
from .config import config_dir

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    Wait = "wait"
    Repeat = "repeat"
    Sequence = "seq"
    NetworkOutage = "outage"
    NetworkDown = "down"
    NetworkRestored = "up"
    MessagePlayersByHandles = "msg_handles"
    MessageAllPlayersExceptHandles = "msg_except_handles"
    MessageGroups = "msg_groups"
    MessageExceptGroups = "msg_except_groups"
    Unknown = "NA"


async def send_message_to_channels(message: str, channel_list):
    task_list = [asyncio.create_task(c.send(message)) for c in channel_list]
    await asyncio.gather(*task_list)


class Event(ABC, BaseModel):
    @abstractmethod
    async def execute(self):
        pass


class SequenceEvent(BaseModel, Event):
    kind: Literal["seq"] = "seq"
    events: list["EventAnnotated"]

    @override
    async def execute(self):
        for event in self.events:
            await event.execute()


class RepeatEvent(BaseModel, Event):
    kind: Literal["repeat"] = "repeat"
    count: int
    event: "EventAnnotated"

    @override
    async def execute(self):
        for _i in range(self.count):
            await self.event.execute()


class WaitEvent(BaseModel, Event):
    kind: Literal["wait"] = "wait"
    time: float

    @override
    async def execute(self):
        await asyncio.sleep(self.time)


class NetworkOutageEvent(BaseModel, Event):
    kind: Literal["outage"] = "outage"
    time: float

    @override
    async def execute(self):
        await SequenceEvent(
            events=[
                NetworkDownEvent(),
                WaitEvent(time=self.time),
                NetworkRestoredEvent(),
            ]
        ).execute()


class NetworkDownEvent(BaseModel, Event):
    kind: Literal["down"] = "down"

    @override
    async def execute(self):
        channel_list = [
            players.get_cmd_line_channel(p) for p in players.get_all_players()
        ]
        await send_message_to_channels(
            "```Error: Network connection lost```", channel_list
        )
        game.set_network_down()


class NetworkRestoredEvent(BaseModel, Event):
    kind: Literal["up"] = "up"

    @override
    async def execute(self):
        channel_list = [
            players.get_cmd_line_channel(p) for p in players.get_all_players()
        ]
        game.set_network_restored()
        await send_message_to_channels(
            "```Network connection restored```", channel_list
        )


class MessagePlayersByHandleEvent:
    def __init__(self, message: str, handles: list[str] = None):
        self.message = message
        self.handles = [] if handles is None else handles

    message: str
    handles: list[str] = []
    groups: list[str] = []

    exclude: bool

    @override
    async def execute(self):
        channel_list = players.get_cmd_line_channels_for_handles(self.handles)
        channel_ids = [c.id for c in channel_list]

        group_channel_list = [
            players.get_cmd_line_channel(c)
            for c in groups.get_members_of_groups(self.groups)
        ]

        channel_list.extend(group_channel_list)

        if self.exclude:
            excluded_channel_list: list[GuildChannel] = []
            for player_id in players.get_all_players():
                channel = players.get_cmd_line_channel(player_id)
                if channel is not None and channel.id not in channel_ids:
                    excluded_channel_list.append(channel)
            await send_message_to_channels(self.message, excluded_channel_list)
        else:
            await send_message_to_channels(self.message, channel_list)


class MessagePlayersByHandleEvent(BaseModel, Event):
    kind: Literal[EventType.MessagePlayersByHandles] = EventType.MessagePlayersByHandles
    message: str
    handles: list[str] = []

    async def execute(self):
        channel_list = players.get_cmd_line_channels_for_handles(self.handles)
        await send_message_to_channels(self.message, channel_list)


class MessagePlayersExceptHandlesEvent:
    kind: Literal[EventType.MessageAllPlayersExceptHandles] = (
        EventType.MessageAllPlayersExceptHandles
    )

    message: str
    handles: list[str] = []

    async def execute(self):
        channel_ids_to_avoid = [
            c.id for c in players.get_cmd_line_channels_for_handles(self.handles)
        ]
        channel_list = []
        for player_id in players.get_all_players():
            channel = players.get_cmd_line_channel(player_id)
            if channel is not None and channel.id not in channel_ids_to_avoid:
                channel_list.append(channel)
        await send_message_to_channels(self.message, channel_list)


# groups:


class MessageGroupsEvent:
    kind: Literal[EventType.MessageGroups] = EventType.MessageGroups

    message: str
    groups: list[str] = []

    async def execute(self):
        channel_list = [
            players.get_cmd_line_channel(c)
            for c in groups.get_members_of_groups(self.groups)
        ]
        for channel in channel_list:
            logger.debug(f"Found channel {channel}")
        await send_message_to_channels(self.message, channel_list)


class MessageExceptGroupsEvent:
    kind: Literal[EventType.MessageExceptGroups] = EventType.MessageExceptGroups

    message: str
    groups: list[str] = []

    async def execute(self):
        channel_ids_to_avoid = [
            players.get_cmd_line_channel(c).id
            for c in groups.get_members_of_groups(self.groups)
        ]
        channel_list = []
        for player_id in players.get_all_players():
            channel = players.get_cmd_line_channel(player_id)
            if channel is not None and channel.id not in channel_ids_to_avoid:
                channel_list.append(channel)
        await send_message_to_channels(self.message, channel_list)


type EventUnion = (
    SequenceEvent
    | RepeatEvent
    | WaitEvent
    | NetworkOutageEvent
    | NetworkDownEvent
    | NetworkRestoredEvent
    | MessagePlayersByHandleEvent
    | MessagePlayersExceptHandlesEvent
    | MessageGroupsEvent
    | MessageExceptGroupsEvent
)

type EventAnnotated = Annotated[EventUnion, Field(discriminator="kind")]


class Scenario:
    def __init__(self, name: str, steps: list[Event] | None = None):
        self.name = name
        self.steps = [] if steps is None else steps

    @staticmethod
    def from_string(string: str):
        obj = Scenario(None)
        loaded_dict = json.loads(string)
        obj.__dict__.update(loaded_dict)
        for i, step_str in enumerate(loaded_dict["steps"]):
            obj.steps[i] = Event.from_string(step_str)
        return obj

    def to_string(self):
        dict_to_save = deepcopy(self.__dict__)
        list_of_strings = [step.to_string() for step in dict_to_save["steps"]]
        dict_to_save["steps"] = list_of_strings
        return json.dumps(dict_to_save)

    async def execute(self):
        logger.info(f'Executing scenario "{self.name}"...')
        for i, step in enumerate(self.steps):
            repetition_string = "" if step.repetitions == 1 else f" x{step.repetitions}"
            logger.info(
                f'Executing step #{i} ({step.event_type}{repetition_string}) of scenario "{self.name}"...'
            )
            await step.execute()
            logger.info(
                f'Finished executing step #{i} ({step.event_type}{repetition_string}) of scenario "{self.name}".'
            )
        logger.info(f'Finished scenario "{self.name}".')


scenarios_conf_dir = "scenarios"
name_index = "___name"


def store_scenario(scenario: Scenario):
    file_name = str(config_dir / scenarios_conf_dir / f"{scenario.name}.conf")
    scenario_conf = ConfigObj(file_name)
    scenario_conf[name_index] = scenario.name
    for i, _step in enumerate(scenario.steps):
        scenario_conf[str(i)] = scenario.steps[i].to_string()
    scenario_conf.write()


def read_scenario(name: str):
    file_name = str(config_dir / scenarios_conf_dir / f"{name}.conf")
    scenario_conf = ConfigObj(file_name)
    if name_index in scenario_conf and scenario_conf[name_index] == name:
        scenario = Scenario(name)
        index = 0
        while str(index) in scenario_conf:
            scenario.steps.append(Event.from_string(scenario_conf[str(index)]))
            index += 1
        return scenario


async def create_scenario(name: str):
    if name is None:
        return "Error: you must give a name for the scenario."
    scenario = Scenario(name)
    scenario.steps.append(
        Event.from_specific_event(NetworkOutageEvent(time_in_seconds=1))
    )
    scenario.steps.append(Event.from_specific_event(NetworkDownEvent()))
    scenario.steps.append(Event.from_specific_event(WaitEvent(time_in_seconds=5)))
    scenario.steps.append(Event.from_specific_event(NetworkRestoredEvent()))
    scenario.steps.append(
        Event.from_specific_event(
            MessagePlayersByHandleEvent(
                message=f"This is a message from {name}.",
                handles=["switch", "trinity_taskbar", "u2701", "u2702"],
            )
        )
    )
    scenario.steps.append(
        Event.from_specific_event(
            MessagePlayersExceptHandlesEvent(
                message=f"This is a secret message from {name}.",
                handles=["switch", "sandwich", "u2701"],
            )
        )
    )

    store_scenario(scenario)


async def run_scenario(name: str):
    if name is None:
        return "Error: you must give a name for the scenario."
    scenario = read_scenario(name)
    await scenario.execute()
