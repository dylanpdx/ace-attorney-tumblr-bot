ARG FUNCTION_DIR="/function"
ARG oe_polyglot_models="en"
FROM python:3.10-slim as build-image

ARG FUNCTION_DIR
RUN mkdir -p ${FUNCTION_DIR}

RUN apt-get update -y
RUN apt-get install tk git libsm6 libxext6 g++ pkg-config libicu-dev -y
RUN pip install --target ${FUNCTION_DIR} git+https://github.com/LuisMayo/objection_engine.git celery redis boto3

WORKDIR ${FUNCTION_DIR}

#####################

FROM python:3.10-slim

ARG FUNCTION_DIR
ARG oe_polyglot_models
RUN mkdir -p ${FUNCTION_DIR}
RUN apt-get update -y && apt-get install -y ffmpeg tk git libicu-dev libxext6 libsm6 && apt-get clean -y

WORKDIR ${FUNCTION_DIR}

COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

RUN for lang in ${oe_polyglot_models}; do \
    # The download command is idempotent
    python -m polyglot download sentiment2.$lang --exit-on-error ;\
  done


COPY setup.py ${FUNCTION_DIR}

# Download extra assets
RUN python setup.py

COPY renderer.py ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "celery", "-A", "renderer", "worker", "--loglevel=info", "-c", "1" ]