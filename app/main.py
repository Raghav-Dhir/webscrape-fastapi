from typing import List
from fastapi import FastAPI
from . import config, db, schema, crud
from .models import Product, ProductScrapeEvent
from cassandra.cqlengine.management import sync_table

settings = config.get_settings()

app = FastAPI()

session = None

@app.on_event("startup")
def on_startup():
    global session
    session = db.get_session()
    sync_table(Product)
    sync_table(ProductScrapeEvent)

@app.get('/')
async def index():
    return {"hello" : "world", "name" : settings.name}

@app.get('/products', response_model=List[schema.ProductListSchema])
async def products_list_view():
    return list(Product.objects.all())

@app.post('/events/scrape')
async def events_scrape_create_view(data : schema.ProductListSchema):
    product, _ = crud.create_scrape_event(data.dict())
    return product

@app.get('/products/{asin}')
async def products_detail_view(asin):
    data = dict(Product.objects.get(asin=asin))
    events = list(ProductScrapeEvent.objects().filter(asin=asin).limit(5))
    events = [schema.ProductScrapeEventDetailSchema(**x) for x in events]
    data["events"] = events
    data["events_url"] = f"/products/{asin}/events"
    return data

@app.get('/products/{asin}/events', response_model=List[schema.ProductScrapeEventDetailSchema])
async def product_scrapes_list_view(asin):
    return list(ProductScrapeEvent.objects().filter(asin=asin))
