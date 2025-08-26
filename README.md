# FNK0050

FNK0050

## Gesture JSON format

Custom movement gestures can be defined as JSON files placed under
`Server/core/movement/gestures/`. The expected schema is::

```
{
  "name": "wave",            // optional, defaults to file name
  "loop": false,              // optional
  "frames": [
    {
      "t": 0,                 // milliseconds from start
      "legs": [[x, y, z], [x, y, z], [x, y, z], [x, y, z]],
      "overrides": {"11": 92} // optional servo channel overrides
    },
    ...
  ]
}
```

Each frame specifies absolute foot positions for all four legs.  Optional
`overrides` can directly command individual servo channels for one-off
effects.
