"""Random emoji generator.

https://unicode.org/emoji/charts/full-emoji-list.html
https://carpedm20.github.io/emoji/
https://raw.githubusercontent.com/carpedm20/emoji/master/emoji/unicode_codes/data_dict.py
"""

import random
from typing import Dict, List

import emoji

EXCLUDED: List[str] = [
    "ball",
    "black",
    "brown",
    "button",
    "clock",
    "cloud",
    "face",
    "flag",
    "globe",
    "green",
    "hand",
    "man",
    "men",
    "medal",
    "moon",
    "people",
    "person",
    "pointing",
    "speak",
    "thirty",
    "white",
    "woman",
    "women",
    "yellow",
]


def sort_results(
    unsorted: Dict[str, str],
) -> Dict[str, str]:
    """Reorder results in sorted order by name string.

     example:
        name: 'thumbs_up'
        unicode: 👍

    Args:
        unsorted (dict): of name/unicode pairs

    Returns:
        dict: sorted mapping by name
    """
    sorted_by_name = {}
    sorted_keys = sorted(unsorted.keys())
    for emoji_name in sorted_keys:
        emoji_icon = unsorted[emoji_name]
        sorted_by_name[emoji_name] = emoji_icon
    return sorted_by_name


def build_emoji_map(
    is_filtered: bool = True,
) -> Dict[str, str]:
    """Create lookup table of emoji icon strings sorted by readable name.

    https://raw.githubusercontent.com/carpedm20/emoji/master/emoji/unicode_codes/data_dict.py

    Args:
        is_filtered (bool): filter list of available emoji:
           not excluded or unicode length > 1

    Returns:
        sorted mapping of readable name to unicode emoji string
    """
    emoji_map = {}
    for emoji_icon in list(emoji.EMOJI_DATA):
        emoji_name = emoji.demojize(emoji_icon, delimiters=("", ""))
        # remove symbols, cast to lowercase
        emoji_name = emoji_name.replace("’", "").replace("-", "_").replace(".", "").lower()
        if is_filtered:
            # ignore any substring from excluded list
            if not any(e in emoji_name for e in EXCLUDED):
                # ignore long unicode emoji strings (countries/flags)
                if len(emoji_icon) == 1:
                    emoji_map[emoji_name] = emoji_icon
        else:
            emoji_map[emoji_name] = emoji_icon
    return sort_results(emoji_map)


EMOJI_MAP = build_emoji_map()


def show_emoji_data() -> None:
    """Display sorted emoji data."""
    for i, (emoji_name, emoji_icon) in enumerate(EMOJI_MAP.items(), start=1):
        print(f"emoji_{i:04d}\t{emoji_name} = {emoji_icon} ({len(emoji_icon)} chars)")


def get_random_emoji(size: int = 1) -> List[str]:
    """Random pick of of n-size emoji unicode strings.

    https://github.com/carpedm20/emoji

    Returns:
        List of emoji unicode strings
    """
    picks: List[str] = []
    # flip negative size to positive
    if size < 1:
        size *= -1
    # ensure termination
    if size > len(EMOJI_MAP):
        size = len(EMOJI_MAP)
    # create unique ordered set
    while len(picks) < size:
        random_name = random.choice(list(EMOJI_MAP.keys()))
        random_emoji = EMOJI_MAP[random_name]
        if random_emoji not in picks:
            picks.append(random_emoji)
    return picks
