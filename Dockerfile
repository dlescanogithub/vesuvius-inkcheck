# CPU-only image: inkcheck + IRP cards. Build: docker build -t inkcheck .
# Run the synthetic example:  docker run --rm -v "$PWD/out:/out" inkcheck \
#   examples/data/synthetic_pred_9.6um.png examples/data/synthetic_ref_19.2um.png \
#   --pred-um 9.6 --ref-um 19.2 --ref-origin 128,128 --out /out/synthetic
# (Real data: run examples/fetch_paris4_example.py on the host and mount examples/data.)
FROM python:3.12-slim
ENV OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install .
COPY examples ./examples
COPY tests ./tests
ENTRYPOINT ["inkcheck"]
