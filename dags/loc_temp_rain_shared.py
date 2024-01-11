import airflow
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

from datetime import timedelta

default_args = {
    "owner": "Airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=3)
}

with DAG(
    dag_id="loc_temp_rain_sharedAvg_daily",
    start_date=airflow.utils.dates.days_ago(1),
    catchup=False,
    default_args=default_args,
    schedule_interval="* 6 * * *",
) as dag:

    refresh_loc_temp_rain_sharedAvg = SnowflakeOperator(
        task_id="refresh_loc_temp_rain_sharedAvg",
        snowflake_conn_id="snowflake.K_BIKE.RAW_DATA_conn",
        # 대여소별 평균 거치율 계산 후
        # 장소 - 기온 - 강수 확률 - 평균 대여율 테이블 생성
        sql=f"""
                DROP TABLE IF EXISTS temp;
                CREATE OR REPLACE TABLE temp AS (
                    SELECT place, (SUM(sbike_shared) / COUNT(sbike_shared)) as sharedAvg
                    FROM sbike
                    WHERE created_at >= DATEADD(day, -7, CURRENT_DATE)
                    GROUP BY place
                );
                
                BEGIN;
                
                DROP TABLE IF EXISTS ANALYTICS.loc_temp_rain_sharedAvg;
                CREATE OR REPLACE TABLE ANALYTICS.loc_temp_rain_sharedAvg AS (
                    SELECT w.place, w.temp, w.rain_chance, t.sharedAvg
                    FROM weather w
                    JOIN temp t on w.place = t.place
                    WHERE created_at >= DATEADD(day, -7, CURRENT_DATE)
                );
                
                COMMIT;
                """,
        # 트랜잭션 실패시 자동으로 ROLLBACK후, DAG 실패처리 (SnowflakeOperator 기본 설정)
        autocommit=True
    )

    refresh_loc_temp_rain_sharedAvg
