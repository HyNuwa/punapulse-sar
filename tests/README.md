# Tests

`make_fake_products.py` writes **synthetic** HDF5 files with the same layout as NISAR GCOV/GUNW. They are used only to check that the pipeline runs end to end without downloading gigabytes. Their outputs are not NISAR data and must never be copied to `docs/data/`.

```bash
python tests/make_fake_products.py tests/_out/raw
PUNAPULSE_RAW_DIR=tests/_out/raw PUNAPULSE_WEB_DATA_DIR=tests/_out/web python -m pipeline.process_gcov
```
