import pytest
import os
import dataclasses
from lambda_function import (
    parse_timestamp,
    format_datetime,
    compose_message,
    get_last_ts,
    LastTS,
    State,
    next_state,
    config_from_env
)


def test_timestamp():
    dt = parse_timestamp(1640259948)
    assert format_datetime(dt) == "2021-12-23 12:45:48 CET"


@pytest.fixture
def state() -> State:
    return {
        "members": {
            "617438": {
                "id": "617438",
                "stars": 0,
                "global_score": 0,
                "last_star_ts": "0",
                "completion_day_level": {},
                "name": "Some Other",
                "local_score": 0,
            },
            "312956": {
                "global_score": 410,
                "last_star_ts": 1640409531,
                "completion_day_level": {
                    "23": {
                        "1": {"get_star_ts": 1640242291},
                        "2": {"get_star_ts": 1640259948},
                    },
                    "9": {
                        "2": {"get_star_ts": 1639026678},
                        "1": {"get_star_ts": 1639026276},
                    },
                    "17": {
                        "1": {"get_star_ts": 1639717637},
                        "2": {"get_star_ts": 1639717808},
                    },
                },
                "name": "Some One",
                "local_score": 1237,
                "id": "312956",
                "stars": 50,
            },
            "949379": {
                "last_star_ts": "0",
                "global_score": 0,
                "completion_day_level": {},
                "name": "emmikkelsen",
                "local_score": 0,
                "id": "949379",
                "stars": 0,
            },
        }
    }


@pytest.fixture
def last_ts(state) -> LastTS:
    last_ts = get_last_ts(state)
    assert last_ts is not None
    return last_ts


def test_compose_message_steady(last_ts, state):
    msg = compose_message(last_ts, state)
    assert msg == ""


def test_compose_message_new_member(last_ts, state):
    del last_ts["members"]["617438"]
    assert (
        compose_message(last_ts, state)
        == "\N{party popper} Some Other joined the board\n"
    )


def test_compose_message_new_star(last_ts, state):
    last_ts["members"]["312956"] = 1640242291
    assert (
        compose_message(last_ts, state)
        == "\N{White Medium Star} Some One has completed day 23 part 2 at 2021-12-23 12:45:48 CET\n"
    )


def test_next_state(last_ts, state):
    del last_ts["members"]["617438"]

    msg = []
    def m(config, message):
        msg.append(message)

    s2 = next_state(None, last_ts, state, m)
    assert s2 and ("617438" in s2["members"])
    assert msg and msg[0].startswith("\N{party popper}")

    msg = []
    s2 = next_state(None, None, state, m)
    assert s2 is not (s2 == get_last_ts(state))
    assert msg==[""]

    msg = []
    s2 = next_state(None, last_ts, None, m)
    assert s2 == last_ts
    assert msg and msg[0].startswith("Unable to connect ")

def test_config_from_env():
    env_dict = {
        "aoc_session_cookie": "5XXXd",
        "slack_webhook_url": "https://hooks.slack.com/services/AAA/BBBB", 
        "aoc_year": "2022",
        "aoc_board": "195216"
    }
    os.environ.update(env_dict)
    config = config_from_env()
    assert dataclasses.asdict(config) == env_dict
