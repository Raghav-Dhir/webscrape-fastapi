from celery import Celery
from celery.schedules import crontab
from . import config, db, models
from celery.signals import beat_init, worker_process_init
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table

celery_app = Celery(__name__)
settings = config.get_settings()

REDIS_URL = settings.redis_url
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL

Product = models.Product
ProductScrapeEvent = models.ProductScrapeEvent

def celery_on_startup(*args, **kwargs):
    if connection.cluster is not None:
        connection.cluster.shutdown()
    if connection.session is not None:
        connection.session.shutdown()
    cluster = db.get_cluster()
    session = cluster.connect()
    connection.register_connection(str(session), session=session)
    connection.set_default_connection(str(session))
    sync_table(Product)
    sync_table(ProductScrapeEvent)

beat_init.connect(celery_on_startup)
worker_process_init.connect(celery_on_startup)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, *args, **kwargs):
    # sender.add_periodic_task(1, random_task.s("gokuldham"), expires=10)
    # sender.add_periodic_task(
    #     crontab(hour=8, minute=0, day_of_week=2),
    #      random_task.s("gokuldham"), expires=10)
    sender.add_periodic_task(
        crontab(minute="*/5"),
        scrape_products.s()
    )

@celery_app.task
def random_task(name):
    print(f"i live in {name} society.")

@celery_app.task
def list_products():
    print(list(Product.objects().all().values_list("asin", flat=True)))

@celery_app.task
def scrape_asin(asin: str):
    print(asin)

@celery_app.task
def scrape_products():
    print("doing scraping")
    q = Product.objects().all().values_list("asin", flat=True)
    for asin in q:
        scrape_asin.delay(asin)