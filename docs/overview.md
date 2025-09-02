# Overview

The server relies on a `config.toml` file located in `Server/app/`. This file
controls which subsystems run and how each one logs information.

## Configuration

```toml
[vision]
enable = true
stream_interval = 0.2
profile = "object"
threshold = 0.5
model_path = "models/default.pt"

[movement]
enable = true

[voice]
enable = true

[led]
enable = true

[hearing]
enable = true

[logging]
enable = true
level = "INFO"
vision = true
movement = false
voice = false
led = false
hearing = false
```

Each subsystem has an `enable` flag. Setting it to `false` prevents the server
from initializing that module, so no resources are used and any calls to the
disabled service are ignored. The `[logging]` section controls the global log
level and which subsystems emit debug information.

`Server/run.py` loads this file at start-up, so no command-line arguments or
environment variables are required.

## Quick Start: Vision and Voice Only

To run only the vision and voice subsystems, disable the others in
`config.toml`:

```toml
[vision]
enable = true

[movement]
enable = false

[voice]
enable = true

[led]
enable = false

[hearing]
enable = false

[logging]
enable = true
level = "INFO"
vision = true
voice = true
movement = false
led = false
hearing = false
```

Start the server with `python Server/run.py` and only vision and voice will be
active.
