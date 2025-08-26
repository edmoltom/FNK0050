# Gestures via JSON (quick template)

**Where to place the JSONs**  
- Put each gesture in a `gestures/` folder next to `controller.py`.  
- The file must be named `<name>.json`. For example, `greet.json` is played with `GestureCmd("greet")` or `GreetCmd`.

**File structure**
```json
{
  "name": "my_gesture",
  "loop": false,
  "frames": [
    { "t": 0, "legs": [[x,y,z],[x,y,z],[x,y,z],[x,y,z]] },
    { "t": 500, "legs": [[...],[...],[...],[...]], "overrides": { "11": 120 } }
  ]
}
```
- `t`: **absolute** time in milliseconds from the start of the gesture.  
- `legs`: **list of 4** positions `[x,y,z]` (mm) in **absolute foot coordinates**.  
  - Typical convention: **X** forward (+), **Y** upward (+), **Z** left (+).  
  - Use your current neutral as reference (you can read it from `controller.point`).  
- `overrides` (optional): dictionary `servo_channel → degrees`. Applied at that frame (e.g., wrist/leg).

**Interpolation and blending**  
- The player interpolates **linearly** between frames at `tick_hz`.  
- If your first frame starts with `t > 0`, the controller **injects the current pose** at `t=0` to avoid jumps.  
- `loop: true` makes the gesture repeat (if your version of `gestures.py` exposes that flag).

**How to play**  
- Create `gestures/<name>.json` and from your app run `GestureCmd("<name>")` (or the shortcut you have).  
- The gait pauses while the gesture runs; once it finishes, everything returns to normal state.

**Tips**  
- Keep `t` **strictly increasing** and in milliseconds.  
- Limit XYZ to safe ranges for your kinematics; validate cold before energizing.  
- For fine “waving,” add several frames with `overrides` separated by 10–20 ms.  

Done! Duplicate the template, adjust `legs/overrides`, and you’ll have new animations without touching Python.  
