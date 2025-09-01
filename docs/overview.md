# Configuration Overview

The server now relies on a `config.toml` file located in `Server/app/`. The
file controls subsystem toggles and logging behaviour. A sample configuration
is provided and looks like:

```toml
[vision]
enable = true
profile = "object"
threshold = 0.5
model_path = "models/default.pt"
log = true

[movement]
enable = true
log = false

[voice]
enable = true
log = false

[led]
enable = true
log = false

[hearing]
enable = true
log = false

[logging]
level = "INFO"
```

`Server/run.py` simply loads this file on start-up and no longer requires
command-line arguments or environment variables. Adjust the values in the TOML
file to enable subsystems like voice, LED, or hearing and tune their logging
preferences alongside vision and movement.
