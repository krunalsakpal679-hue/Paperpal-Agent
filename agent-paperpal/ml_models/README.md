# ml_models/README.md
# ML Model Artifacts

This directory stores spaCy and HuggingFace model artifacts
used by the DocParseAgent for NLP-based document element classification.

## Models Used

- **spaCy `en_core_web_sm`** — Base English NLP model (installed at Docker build time)
- **Custom NER model** — Fine-tuned for academic document element recognition (TBD)

## Notes

- Large model files (.bin, .pt, .onnx) are gitignored
- Models are downloaded during Docker build or via setup scripts
- For production, models should be stored in S3 and cached locally
