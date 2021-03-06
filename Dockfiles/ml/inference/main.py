import tensorflow as tf
from tensorflow.keras.models import load_model
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import kydb

DBNAME = 's3://epython'
MODEL_PATH = '/ml/models/fx_btc_jpy_model.h5'


class ModelManager:

    def __init__(self, dbname, model_path):
        self.dbname = dbname
        self.model_path = model_path
        self._cached_model = None
        self.reload_model()

    def reload_model(self):
        self._cached_model = self.load_model()

    def load_model(self):
        db = kydb.connect(self.dbname)
        data = db[self.model_path]
        filename = self.model_path.rsplit('/', 1)[1]
        with open(filename, 'wb') as f:
            f.write(data)

        return load_model(filename)

    def get_model(self):
        if not self._cached_model:
            self.reload_model()

        return self._cached_model


class TrainedModel(BaseModel):
    dbame: str
    model_path: str


class MarketData(BaseModel):
    hist_prices: List[float]


model_manager = ModelManager(DBNAME, MODEL_PATH)
app = FastAPI()


@app.post('/reload_model/')
async def reload_model(model: TrainedModel):
    model_manager.dbname = model.dbame
    model_manager.model_path = model.model_path
    model_manager.reload_model()


def _normalise_prices(prices):
    min_price = max_price = prices[0]
    for p in prices[1:]:
        if p < min_price:
            min_price = p
        elif p > max_price:
            max_price = p

    diff = (max_price - min_price)
    return [(x - min_price) / diff for x in prices]


@app.post('/recommend/')
async def recommend(marketdata: MarketData):
    model = model_manager.get_model()
    prices = _normalise_prices(marketdata.hist_prices)
    res = model.predict([prices])[:, 1][0]
    return 1 if res >= 0.5 else 0
