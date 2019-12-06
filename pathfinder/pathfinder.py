from collections import OrderedDict
from typing import List, Tuple
from zero_ex.contract_wrappers.exchange.types import Order, OrderInfo, OrderStatus
from zero_ex.sra_client import ApiClient, Configuration, DefaultApi
from zero_ex.order_utils import asset_data_utils
import networkx as nx
import random

from .order_graph import OrderGraph


TOKENS = {
    "USDC": "0x"
    + asset_data_utils.encode_erc20("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48").hex(),
    "WETH": "0x"
    + asset_data_utils.encode_erc20("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2").hex(),
    "ZRX": "0x"
    + asset_data_utils.encode_erc20("0xe41d2489571d322189246dafa5ebde1f4699f498").hex(),
    "SAI": "0x"
    + asset_data_utils.encode_erc20("0x89d24a6b4ccb1b6faa2625fe562bdd9a23260359").hex(),
    "BAT": "0x"
    + asset_data_utils.encode_erc20("0x0d8775f648430679a709e98d2b0cb6250d2887ef").hex(),
}


class Pathfinder:
    def __init__(self,) -> None:
        self.orderGraph = OrderGraph([])

        # TODO: Get orders from other relayers
        radarConfig = Configuration()
        radarConfig.host = "http://api.radarrelay.com/0x"
        self.radarApi = DefaultApi(ApiClient(radarConfig))

    def market_sell_path(
        self, takerAssetData: str, makerAssetData: str, sellAmount: int
    ) -> Tuple[OrderedDict, int, int]:
        routes = nx.all_simple_paths(
            self.orderGraph, source=takerAssetData, target=makerAssetData, cutoff=3
        )
        fills = OrderedDict()
        amountSold = 0
        amountBought = 0

        while amountSold < sellAmount:
            bestPaths = [
                self.orderGraph.market_sell_best_path(route, sellAmount - amountSold)
                for route in routes
            ]
            optimalPath, optimalAmountBought = max(bestPaths, key=lambda x: x[1])

            for orderHash, fillAmount in optimalPath:
                if orderHash not in fills:
                    fills[orderHash] = fillAmount
                else:
                    fills[orderHash] += fillAmount
                self.orderGraph.simulate_fill(orderHash, fillAmount)

            amountSold += optimalPath[0][
                1
            ]  # fillAmount for the first order in the path
            amountBought += optimalAmountBought

        return (fills, amountSold, amountBought)

    def execute_sell(
        self, takerAssetData: str, makerAssetData: str, sellAmount: int, maxPrice: float
    ) -> None:
        fills, amountSold, amountBought = self.market_sell_path(
            takerAssetData, makerAssetData, sellAmount
        )
        if amountSold / amountBought > maxPrice:
            raise Exception("Cannot satisfy price requirement")
        # batchFillOrdersNoThrow

    def market_buy_path(
        self, takerAssetData: str, makerAssetData: str, buyAmount: int
    ) -> List[Tuple[Order, int]]:
        pass

    # TODO: Get the orders we care about
    def get_orders(self) -> List[Order]:
        tokenPairs = [
            (TOKENS["WETH"], TOKENS["SAI"]),
            (TOKENS["WETH"], TOKENS["USDC"]),
            (TOKENS["WETH"], TOKENS["ZRX"]),
            (TOKENS["WETH"], TOKENS["BAT"]),
        ]
        orders = []
        for pair in tokenPairs:
            response = self.radarApi.get_orderbook(
                base_asset_data=pair[0], quote_asset_data=pair[1]
            )
            orders = (
                orders
                + [record.order for record in response.bids.records]
                + [record.order for record in response.asks.records]
            )
        return orders

    # Stubbed out for now
    def get_order_info(self, orders: List[Order]) -> List[OrderInfo]:
        return [
            OrderInfo(
                orderStatus=OrderStatus.FILLABLE,
                orderHash=hex(random.getrandbits(256)),
                orderTakerAssetFilledAmount=0,
            )
            for order in orders
        ]

    def update_order_graph(self) -> None:
        orders = self.get_orders()
        orderInfo = self.get_order_info(orders)
        self.orderGraph.batch_update(orders, orderInfo)
