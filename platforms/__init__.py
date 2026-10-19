"""Реестр сетей. Чтобы добавить новую сеть: создайте модуль с LIMIT и publish() и добавьте его сюда."""
from . import bluesky, telegram, threads

PUBLISHERS = {
    "bluesky": bluesky,
    "telegram": telegram,
    "threads": threads,
}
