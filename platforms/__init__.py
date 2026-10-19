"""Network registry. To add a network: create a module with LIMIT and publish() and register it here."""
from . import bluesky, telegram, threads

PUBLISHERS = {
    "bluesky": bluesky,
    "telegram": telegram,
    "threads": threads,
}
