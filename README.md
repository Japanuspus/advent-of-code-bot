# Advent of Code bot

A bot for pushing updates about the Kvantify [advent of code]()-leaderboard to slack.

The system moving parts consist of
- An AWS lambda that takes previous AOC-state as input and returns current AOC state while posting any changes to the slack channel.
- As AWS state machine that calls the lambda function.
- (in progress) A GitHub action that updates the lambda function when changes are merged to main.


## Start of season update

- Update production env file
- Commit to AWS lambda via script
- Start new execution of the state machine

