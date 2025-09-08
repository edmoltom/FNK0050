# Logging

The server application records runtime information to a rotating log file named `robot.log` at the root of the project.
The log keeps up to three rotations, each limited to 1&nbsp;MB.

To monitor activity in real time, run:

```bash
tail -f robot.log
```

You can also inspect older entries with tools such as `less` or `grep`.

