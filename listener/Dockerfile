ARG FUNCTION_DIR="/function"
FROM python:3.10-slim as build-image

ARG FUNCTION_DIR
RUN mkdir -p ${FUNCTION_DIR}

RUN pip install --target ${FUNCTION_DIR} boto3 PyTumblr2==0.2.4 celery redis

WORKDIR ${FUNCTION_DIR}

#####################

FROM python:3.10-slim

ARG FUNCTION_DIR
RUN mkdir -p ${FUNCTION_DIR}

WORKDIR ${FUNCTION_DIR}

COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

COPY listener.py ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python","-u", "listener.py" ]