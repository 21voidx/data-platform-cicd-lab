ARG AIRFLOW_VERSION=3.3.0

FROM apache/airflow:${AIRFLOW_VERSION}

ARG AIRFLOW_VERSION

COPY requirements.txt /requirements.txt

RUN if [ -s /requirements.txt ]; then \
      pip install \
        --no-cache-dir \
        "apache-airflow==${AIRFLOW_VERSION}" \
        -r /requirements.txt ; \
    fi

COPY \
  --chown=airflow:root \
  dags/ \
  /opt/airflow/dags/
