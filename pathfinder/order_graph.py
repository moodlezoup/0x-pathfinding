from typing import List, Tuple
from zero_ex.contract_wrappers.exchange.types import Order, OrderInfo, OrderStatus
import networkx as nx
import matplotlib.pyplot as plt


class OrderGraph(nx.MultiDiGraph):
    def __init__(self, orders: List[Order], orderInfos: List[OrderInfo] = []) -> None:
        """Constructs the multi-graph representations for the given orders."""
        if len(orders) != len(orderInfos):
            raise Exception("Number of orders must match number of orderInfo's")

        nx.MultiDiGraph.__init__(self)

        self.orders = {}
        self.orderInfo = {}
        for order, orderInfo in zip(orders, orderInfos):
            self.add_order(order, orderInfo)

    def add_order(self, order: Order, orderInfo: OrderInfo) -> None:
        if orderInfo["orderHash"] in self.orders:
            raise Exception("Order already exists in graph")

        if orderInfo["orderStatus"] != OrderStatus.FILLABLE:
            raise Exception("Order is not fillable")

        self.orders[orderInfo["orderHash"]] = order
        self.orderInfo[orderInfo["orderHash"]] = orderInfo
        self.add_edge(
            order["takerAssetData"], order["makerAssetData"], key=orderInfo["orderHash"]
        )

    def remove_order(self, orderHash: str) -> None:
        if orderHash not in self.orders:
            raise Exception("Order not found in graph")

        order = self.orders[orderHash]
        del self.orders[orderHash]
        del self.orderInfo[orderHash]
        self.remove_edge(
            order["takerAssetData"], order["makerAssetData"], key=orderHash
        )

    def update_order(self, orderInfo: OrderInfo) -> None:
        if orderInfo["orderHash"] not in self.orders:
            raise Exception("Order not found in graph")

        if orderInfo["orderStatus"] != OrderStatus.FILLABLE or int(
            orderInfo["orderTakerAssetFilledAmount"]
        ) >= int(self.orders[orderInfo["orderHash"]]["takerAssetAmount"]):
            self.remove_order(orderInfo["orderHash"])
        else:
            self.orderInfo[orderInfo["orderHash"]] = orderInfo

    def simulate_fill(self, orderHash: str, fillAmount: int) -> None:
        if orderHash not in self.orders:
            raise Exception("Order not found in graph")

        orderInfo = self.orderInfo[orderHash]
        orderInfo["orderTakerAssetFilledAmount"] += fillAmount
        self.update_order(orderInfo)

    def batch_update(self, orders: List[Order], orderInfos: List[OrderInfo]) -> None:
        if len(orders) != len(orderInfos):
            raise Exception("Number of orders must match number of orderInfo's")

        for order, orderInfo in zip(orders, orderInfos):
            if orderInfo["orderHash"] not in self.orders:
                self.add_order(order, orderInfo)
            else:
                self.update_order(orderInfo)

    def best_order(self, takerAssetData: str, makerAssetData: str) -> str:
        orderHashes = self[takerAssetData][makerAssetData].keys()
        # TODO: Account for fees
        return max(
            orderHashes,
            key=lambda orderHash: int(self.orders[orderHash]["makerAssetAmount"])
            / int(self.orders[orderHash]["takerAssetAmount"]),
        )

    def market_sell_best_path(
        self, route: List[str], sellAmount: int
    ) -> Tuple[List[Tuple[str, int]], int]:
        path = []
        currentAssetAmount = sellAmount

        for takerAssetData, makerAssetData in zip(route[:-1], route[1:]):
            orderHash = self.best_order(takerAssetData, makerAssetData)
            order = self.orders[orderHash]

            fillableAmount = int(order["takerAssetAmount"]) - int(
                self.orderInfo[orderHash]["orderTakerAssetFilledAmount"]
            )
            fillAmount = min(fillableAmount, currentAssetAmount)
            currentAssetAmount = (
                fillAmount
                * int(order["makerAssetAmount"])
                // int(order["takerAssetAmount"])
            )  # TODO: I think the rounding is a bit off here

            path.append((orderHash, fillAmount))

        return (path, currentAssetAmount)

    def market_buy_best_path(
        self, route: List[str], buyAmount: int
    ) -> List[Tuple[str, int]]:
        pass

    def draw(self) -> None:
        nx.draw(self)
        plt.draw()
