import itertools

highest_ever_index = "___highest_ever"
system_role_name = "system"
admin_role_name = "admin"
new_player_role_name = "new_player"
player_role_name = "player"

type_player = "player"
type_shop = "shop"

forbidden_content = "**"
forbidden_content_print = r"\*\*"

transaction_collector = "___collector"
transaction_collected = "___collected"

coin = "¥"
hard_space = "   "

# good-to-have emojis:
# ✅
# ❇️
# ❌
# 🟥
# 🔥
emoji_cancel = "❌"
emoji_open = "❇️"
emoji_accept = "✅"
emoji_green = "🟢"
emoji_red = "🔴"
emoji_green_book = "📗"
emoji_red_book = "📕"

emoji_alert = "❗"
emoji_unavail = "🚫"
emoji_unread = "💬"

number_emojis = [
    "0️⃣",
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
]

letter_emojis = [
    "🇦",
    "🇧",
    "🇨",
    "🇩",
    "🇪",
    "🇫",
    "🇬",
    "🇭",
    "🇮",
    "🇯",
    "🇰",
    "🇱",
    "🇲",
    "🇳",
    "🇴",
    "🇵",
    "🇶",
    "🇷",
    "🇸",
    "🇹",
    "🇺",
    "🇻",
    "🇽",
    "🇾",
    "🇿",
]


""" def letter_emoji(letter: str):
    initial = letter.lower()[0]
    string = f":regional_indicator_{initial}:"
    return emoji.emojize(string, language="alias") """


def letter_emoji(letter: str) -> str:
    code = ord(letter.lower()[0])
    return letter_emojis[code - 97]


# Channels
shops_category_name = "public_business"
off_category_name = "offline"
public_open_category_name = "Local network"
shadowlands_category_name = "shadowlands"
groups_category_name = "private_networks"
announcements_category_name = "announcements"
gm_announcements_name = "gm_alerts"
setup_category_name = "setup"
testing_category_name = "testing"
personal_category_base = "personal_account_"
chats_category_base = "chats_"
num_per_player_category_groups = (
    12  # 11 for regular players, one for non-player entities
)


base_categories = [
    (off_category_name, ["off_general", "off_teknikhjälp"]),
    (setup_category_name, ["landing_page"]),
    (announcements_category_name, [gm_announcements_name]),
    (testing_category_name, ["cmd_line_gm", "off_intrig"]),
    (shadowlands_category_name, ["seattle_news", "open_channel", "anon"]),
    (public_open_category_name, ["marketplace", "you_are_drunk"]),
    (shops_category_name, []),
    (groups_category_name, []),
]

pa_categories = [
    (personal_category_base + str(i), []) for i in range(num_per_player_category_groups)
]
chats_categories = [
    (chats_category_base + str(i), []) for i in range(num_per_player_category_groups)
]


def get_all_categories():
    return itertools.chain(base_categories, pa_categories, chats_categories)


# Roles
all_players_role_name = "251"
shop_role_start = 2300
player_personal_role_start = 2700
group_role_start = 2900

# personal_role_regex = re.compile(f'^27[0-9][0-9]$')
# shop_role_regex = re.compile(f'^23[0-9][0-9]$')


def is_shop_role(name: str):
    try:
        number = int(name)
        return number >= shop_role_start and number < player_personal_role_start
    except ValueError:
        return False


def is_player_role(name: str):
    try:
        number = int(name)
        return number >= player_personal_role_start and number < group_role_start
    except ValueError:
        return False


def is_group_role(name: str):
    try:
        number = int(name)
        return number >= group_role_start
    except ValueError:
        return False
