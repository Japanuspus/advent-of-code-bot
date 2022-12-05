"""
advent-of-code-bot AWS lambda function

Code lives on kvantify github.
Janus, 2022
"""
from __future__ import annotations
import dataclasses
from datetime import datetime
import json
import os
import typing
from urllib import request
from zoneinfo import ZoneInfo


# typed dicts for AOC response hinting
NullOrTS = typing.Union[typing.Literal["0"], int]


class Completion(typing.TypedDict):
    get_star_ts: int


class Member(typing.TypedDict):
    id: str
    name: str
    stars: int
    last_star_ts: NullOrTS
    completion_day_level: dict[str, dict[str, Completion]]


class State(typing.TypedDict):
    """
    Type of json-responce from AOC
    """

    members: dict[str, Member]


class LastTS(typing.TypedDict):
    """
    Type of state persisted by state machine
    """

    members: dict[str, NullOrTS]


output_tz = ZoneInfo("Europe/Copenhagen")


@dataclasses.dataclass(frozen=True)
class Config:
    aoc_year: str
    aoc_board: str
    aoc_session_cookie: str
    slack_webhook_url: str


def config_from_env() -> Config:
    def env_or_fail(env_name) -> str:
        if (value:=os.getenv(env_name, default=None)) is None:
            raise RuntimeError(f'Value for "{env_name}" not defined in environment')
        return value

    fields = dataclasses.fields(Config)
    return Config(**{f.name: str(env_or_fail(f.name)) for f in fields})


def get_last_ts(state: State) -> None | LastTS:
    if (members := state.get("members", None)) is not None:
        return {"members": {m: d["last_star_ts"] for m, d in members.items()}} 
    return None

def get_aoc_state(cfg: Config) -> None | State:
    """
    Retrive leaderboard state from aoc

    If no session cookie is included (which will never happen here), aoc redirects to the main
    leaderboard but returns status 200.
    If an invalid session cookie is included, urlopen will fail.
    """
    aoc_url = f"https://adventofcode.com/{cfg.aoc_year}/leaderboard/private/view/{cfg.aoc_board}.json"
    url = request.Request(
        aoc_url, headers={
            "Cookie": f"session={cfg.aoc_session_cookie}",
            # https://old.reddit.com/r/adventofcode/comments/z9dhtd/please_include_your_contact_info_in_the_useragent/
            "User-Agent": "github.com/japanuspus/advent-of-code-bot by @japanuspus"
        }
    )

    try:
        with request.urlopen(url) as conn:
            if not conn.status == 200:
                print(f"Unexpexted status from aoc: {conn}")
                return None
            result_string = conn.read()
    except request.HTTPError as e:
        print(f"HTTP error: {e}")
        return None

    try:
        result = json.loads(result_string)
    except json.JSONDecodeError as e:
        print(f"Response from aoc not valid json: {e}")
        return None

    if "members" not in result:
        print(f"Received unexpected json format from aoc: {result}")
        return None

    return result


def parse_timestamp(ts):
    return datetime.fromtimestamp(ts, output_tz)


def format_datetime(t) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S %Z").rstrip()


K = typing.TypeVar("K")
V = typing.TypeVar("V")


def items_sorted(d: dict[K, V]) -> list[tuple[K, V]]:
    return sorted(d.items(), key=lambda kv: int(kv[0]))


def compose_message(previous_last_ts: LastTS, current_state: State) -> str:
    # members
    current = current_state["members"]
    previous = previous_last_ts["members"]
    msg = ""
    # New joins
    for m, member in current.items():
        if m not in previous:
            msg += f"\N{party popper} {member['name']} joined the board\n"
    # New stars
    for m, member in current.items():
        last_ts = previous.get(m, "0")
        if member["last_star_ts"] == last_ts:
            continue
        for day, parts in items_sorted(member["completion_day_level"]):
            for part, v_ts in items_sorted(parts):
                ts = v_ts["get_star_ts"]
                if last_ts == "0" or ts > last_ts:
                    ts_str = format_datetime(parse_timestamp(ts))
                    msg += f"\N{White Medium Star} {member['name']} has completed day {day} part {part} at {ts_str}\n"
    return msg


def submit_message(config: Config, msg: str):
    if msg is None or len(msg.strip()) == 0:
        print("Empty message, not submitting to Slack")
        return

    url = request.Request(
        config.slack_webhook_url,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    res = request.urlopen(url, data=bytes(json.dumps({"text": "\n" + msg}), "utf-8"))
    if not res.status == 200:
        raise Exception(f"Error submitting to slack: {res}")


def next_state(
    config: Config, previous_last_ts: None | LastTS, current_state: None | State, message_hook=submit_message
) -> None | LastTS:
    if current_state is None:
        # not triggering: urllib raises exception on status 5xx
        msg = "Unable to connect to advent of code leaderboard. Please check logs."
    elif previous_last_ts is None:
        msg = ""
    else:
        msg = compose_message(previous_last_ts, current_state)
    message_hook(config, msg)

    if current_state is None:
        # unable to reach aoc, retain last known ts
        return previous_last_ts

    return get_last_ts(current_state)


def check_last_ts(event) -> None | LastTS:
    if (event is not None) and ("members" not in event):
        return None
    return event


def lambda_handler(event, context) -> None | LastTS:
    """
    This is the entry-point used by AWS lambda

    Called from AWS state machine with previous output as input
    """
    print("Lambda function ARN:", context.invoked_function_arn)
    print("CloudWatch log stream name:", context.log_stream_name)
    print("CloudWatch log group name:", context.log_group_name)
    print("Lambda Request ID:", context.aws_request_id)

    config = config_from_env()
    print(f"Obtained config: year={config.aoc_year}, board={config.aoc_board}")
    last_ts = check_last_ts(event)
    if last_ts is None:
        print("Received invalid previous last_ts. Initializing?")
    current_state = get_aoc_state(config)
    print(f"Obtained aoc state: {current_state}")
    next_last_ts = next_state(config, previous_last_ts=last_ts, current_state=current_state)
    print(f"Obtained next last_ts: {next_last_ts}")
    return next_last_ts


def main():
    import argparse
    from textwrap import dedent

    p = argparse.ArgumentParser(
        description=dedent(
            """
        CLI access to lambda handler functionality
    """
        ).strip()
    )
    p.add_argument("input", type=argparse.FileType("r"))
    p.add_argument("output", type=argparse.FileType("w"))
    p.add_argument(
        "--env-file", type=argparse.FileType("r"), help="json dict of env vars"
    )
    p.add_argument("--post-to-slack", action="store_true", help="Post output to slack")
    args = p.parse_args()

    if args.env_file is None:
        config = config_from_env()
    else:
        config = Config(**json.load(args.env_file))

    buf = []
    def buf_msg(config, msg):
        buf.append(msg)
        if args.post_to_slack:
            submit_message(config, msg)

    s1 = check_last_ts(json.load(args.input))
    current_state = get_aoc_state(config)
    s2 = next_state(config, previous_last_ts=s1, current_state=current_state, message_hook=buf_msg)
    for i, msg in enumerate(buf):
        print(f"### Submitted msg no. {i}\n{msg}")
    json.dump(s2, args.output)


if __name__ == "__main__":
    main()
