import logging

import discord
from discord import Interaction, TextStyle, app_commands, ui, utils
from discord.app_commands.errors import MissingRole, NoPrivateMessage
from discord.ext import commands

from talesbot import (
    artifacts,
    gm,
    handles,
    player_setup,
    scenarios,
)

from ..errors import ReportError

logger = logging.getLogger(__name__)


class ArtifactCreateModal(ui.Modal, title="Create Artifact"):
    name = ui.TextInput(label="Code name", required=True)
    password = ui.TextInput(label="Password", required=False)
    content = ui.TextInput(
        label="Body", style=TextStyle.long, required=True, max_length=2000
    )
    announcment = ui.TextInput(label="GM Announcment", required=False)

    async def on_submit(self, interaction: Interaction) -> None:
        password = self.password.value if self.password.value != "" else None
        announcment = self.announcment.value if self.announcment.value != "" else None
        try:
            artifacts.create(
                self.name.value,
                self.content.value,
                password=password,
                announcement=announcment,
            )
        except Exception as e:
            raise ReportError("Failed to create artifact") from e

        await interaction.response.send_message(
            f"Created artifact {self.name.value}", ephemeral=True
        )

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error("Failed to create artifact", exc_info=error)
        await interaction.response.send_message(
            "Failed to create artifact", ephemeral=True
        )


class ArtifactUpdateModal(ui.Modal, title="Update Artifact"):
    content = ui.TextInput(
        label="Body", style=TextStyle.long, required=True, max_length=2000
    )

    def __init__(self, name: str, content: str, page: int | None) -> None:
        self.content.default = content
        self.name = name
        self.page = page

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            artifacts.update(self.name, self.content.value, self.page)
        except Exception as e:
            raise ReportError("Failed to update artifact") from e

        await interaction.response.send_message(
            f"Updated artifact {self.name}", ephemeral=True
        )

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error("Failed to update artifact", exc_info=error)
        await interaction.response.send_message(
            "Failed to update artifact", ephemeral=True
        )


@app_commands.guild_only()
class GmCog(commands.GroupCog, group_name="gm"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def interaction_check(self, interaction: Interaction) -> bool:
        """Check for gm role"""
        if isinstance(interaction.user, discord.User):
            raise NoPrivateMessage()

        role = utils.get(interaction.user.roles, name=gm.role_name)

        if role is None:
            raise MissingRole(gm.role_name)
        return True

    @app_commands.command(
        description="Add a player's handle before they join the server",
    )
    async def add_known_handle(self, interaction: Interaction, handle_id: str):
        player_setup.add_known_handle(handle_id)
        await interaction.response.send_message(
            (
                f"Added entry for {handle_id}. Please update its contents manually "
                "by editing the file"
            ),
            ephemeral=True,
        )

    scenario_g = app_commands.Group(name="scenario", description="Manage scenarios")

    @scenario_g.command(name="run", description="Run a scenario")
    async def run_scenario(self, interaction: Interaction, name: str):
        report = await scenarios.run_scenario(name)
        if report is None:
            report = "Command finished without any output"
        await interaction.response.send_message(report, ephemeral=True)

    @scenario_g.command(name="create", description="Create a basic scenario")
    async def create_scenario(self, interaction: Interaction, name: str):
        report = await scenarios.create_scenario(name)
        if report is None:
            report = "Command ended without any output"
        await interaction.response.send_message(report, ephemeral=True)

    artifact_g = app_commands.Group(name="artifact", description="Manage artifacts")

    @artifact_g.command(name="create", description="Create a artifact interactivly")
    async def create_artifact_interactive(self, interaction: Interaction):
        await interaction.response.send_modal(ArtifactCreateModal())

    @artifact_g.command(name="update", description="Update a artifact interactivly")
    async def update_artifact_interactive(
        self, interaction: Interaction, name: str, page: int | None
    ):
        contents = artifacts.get(name)
        content = contents[page] if page else ""
        await interaction.response.send_modal(
            ArtifactUpdateModal(name=name, content=content, page=page)
        )

    @artifact_g.command(
        name="list",
        description="List all artifacts.",
    )
    async def list_artifact(self, interaction: Interaction):
        artifact_list = artifacts.list_all()
        body = "\n".join(artifact_list)
        await interaction.response.send_message(
            f"Registered artifacts\n```\n{body}\n```", ephemeral=True
        )

    @app_commands.command(description="Reinitialise the GM context and handles.")
    async def init(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        async with handles.semaphore():
            await gm.init(clear_all=True)
        await interaction.followup.send("Done.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GmCog(bot))
