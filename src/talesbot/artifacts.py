import os
from typing import cast

import frontmatter

from talesbot.config import config_dir

artifact_conf_dir = "artifacts"


def create(
    name: str,
    content: str,
    password: str | None = None,
    announcement: str | None = None,
):
    file = config_dir / artifact_conf_dir / f"{name}.md"
    with open(file, "x") as f:
        c = dump_body(parse_body(content))
        post = frontmatter.Post(c, password=password, announcement=announcement)
        frontmatter.dump(post, f)


def update(name: str, content: str, page: int | None = None):
    file = config_dir / artifact_conf_dir / f"{name}.md"
    with open(file, "w+") as f:
        post = frontmatter.load(f)
        pages = parse_body(post.content)

        if page:
            pages.insert(page, content)
        else:
            pages.append(content)

        post.content = dump_body(pages)

        frontmatter.dump(post, f)


def access(name: str, password: str | None = None):
    file = config_dir / artifact_conf_dir / f"{name}.md"
    if not os.path.isfile(file):
        return None, None

    with open(file) as f:
        post = frontmatter.load(f)
        if password and post.get("password") != password:
            return None, None

        return parse_body(post.content), cast(str | None, post.get("announcement"))


def get(name: str):
    file = config_dir / artifact_conf_dir / f"{name}.md"
    with open(file) as f:
        post = frontmatter.load(f)

        return parse_body(post.content)


def list_all():
    return [os.path.basename(n) for n in os.listdir(config_dir / artifact_conf_dir)]


def parse_body(text: str):
    return [p.strip() for p in text.split("===\n")]


def dump_body(pages: list[str]):
    ps = [p.strip() for p in pages]
    return "===\n".join(ps)
