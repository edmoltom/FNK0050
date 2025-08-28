# Migration Notes

- The legacy profile manager and bundled profile files have been removed.
- Detector settings for `big` and `small` are now defined in `Server/core/vision/config/vision.yaml`.
- `DetectorsConfig` instantiates both detectors with default settings and applies any overrides from the YAML configuration.
