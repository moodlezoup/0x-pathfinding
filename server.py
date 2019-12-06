from flask import Flask, json
from pathfinder.pathfinder import Pathfinder, TOKENS

api = Flask(__name__)
pf = Pathfinder()


@api.route("/update", methods=["POST"])
def update():
    pf.update_order_graph()
    return json.dumps({"success": True}), 201


@api.route("/orders", methods=["GET"])
def orders():
    return json.dumps(pf.orderGraph.orders)


@api.route("/order_info", methods=["GET"])
def order_info():
    return json.dumps(pf.orderGraph.orderInfo)


@api.route("/order_graph", methods=["GET"])
def order_graph():
    nodes = list(TOKENS.values())
    links = [
        {"source": order["takerAssetData"], "target": order["makerAssetData"]}
        for order in pf.orderGraph.orders.values()
    ]
    return json.dumps({"nodes": nodes, "links": links})


@api.route(
    "/sell/<string:takerAssetData>/<string:makerAssetData>/<int:amount>",
    methods=["GET"],
)
def sell(takerAssetData: str, makerAssetData: str, amount: int):
    path, amountSold, amountBought = pf.market_sell_path(
        takerAssetData, makerAssetData, amount
    )
    return json.dumps(
        {"path": path, "amountSold": amountSold, "amountBought": amountBought}
    )


if __name__ == "__main__":
    api.run()
