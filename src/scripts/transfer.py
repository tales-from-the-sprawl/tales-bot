import os
from typing import IO

import click
import requests
from configobj import ConfigObj
from pyfzf.pyfzf import FzfPrompt
from requests.auth import HTTPBasicAuth

handles_to_actors = "___handle_to_actor_mapping"

password = os.getenv("TALES_PASS")
assert password is not None
auth = HTTPBasicAuth("tales", password)


@click.command()
@click.argument("handles_file", type=click.File(), required=True)
def main(handles_file: IO):
    fzf = FzfPrompt()
    handles_conf = ConfigObj(handles_file)
    handles = ["[credstick]"] + [handle for handle in handles_conf[handles_to_actors]]

    body: dict[str, str] = {}

    [sender] = fzf.prompt(handles, "--ghost='Select sender'")
    if sender != "[credstick]":
        body["sender"] = sender
    [receiver] = fzf.prompt(handles, "--ghost='Select receiver'")
    if receiver != "[credstick]":
        body["receiver"] = receiver
    body["amount"] = click.prompt("Amount", type=click.INT)

    print(body)

    requests.post("https://talesbot.codegrotto.com/api/transfer", body, auth=auth)
    pass


if __name__ == "__main__":
    main()
