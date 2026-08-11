import pendulum

from airflow.sdk import dag, task


@dag(
    dag_id="hello_cicd",
    schedule=None,
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="UTC",
    ),
    catchup=False,
    tags=["cicd"],
)
def hello_cicd():

    @task
    def hello():
        print("Airflow deployed through GitHub Actions")

    hello()


hello_cicd()
