import requests
import urllib.parse
import datetime
import json
import gspread
from creds import credentials
from dataclasses import dataclass, asdict

# Getting the LWA access token using the Seller Central App credentials. The token will be valid for 1 hour until it expires.
token_response = requests.post(
    "https://api.amazon.com/auth/o2/token",
    data={
        "grant_type": "refresh_token",
        "refresh_token": credentials["refresh_token"],
        "client_id": credentials["lwa_app_id"],
        "client_secret": credentials["lwa_client_secret"],
    },
)
access_token = token_response.json()["access_token"]

# North America SP API endpoint (from https://developer-docs.amazon.com/sp-api/docs/sp-api-endpoints)
endpoint = "https://sellingpartnerapi-na.amazon.com"

# US Amazon Marketplace ID (from https://developer-docs.amazon.com/sp-api/docs/marketplace-ids)
marketplace_id = "ATVPDKIKX0DER"

# Downloading orders (from https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorders)
# the getOrders operation is a HTTP GET request with query parameters
request_params = {
    "MarketplaceIds": marketplace_id,  # required parameter
    "CreatedAfter": (
            datetime.datetime.now() - datetime.timedelta(days=30)
    ).isoformat(),  # orders created since 30 days ago, the date needs to be in the ISO format
}

orders = requests.get(
    endpoint
    + "/orders/v0/orders"  # getOrders operation path (from https://developer-docs.amazon.com/sp-api/docs/orders-api-v0-reference#getorders)
    + "?"
    + urllib.parse.urlencode(request_params),  # encode query parameters to the URL
    headers={
        "x-amz-access-token": access_token,  # access token from LWA, every SP API request needs to have this header
    },
)


# # pretty print the JSON response
# print(json.dumps(orders.json(), indent=2))


@dataclass
class AmazonOrder:
    order_id: str
    purchase_date: str
    order_status: str
    order_total: str
    payment_method: str
    marketplace_id: str
    shipment_service_level_category: str
    order_type: str


HEADER = [
    "AmazonOrderId",
    "PurchaseDate",
    "OrderStatus",
    "OrderTotal",
    "PaymentMethod",
    "MarketplaceId",
    "ShipmentServiceLevelCategory",
    "OrderType",
]

if __name__ == '__main__':

    # authenticate
    gc = gspread.service_account(filename='keys.json')
    sh = gc.open("test_123")
    worksheet = sh.get_worksheet(0)

    # write header
    data = worksheet.get_all_values()
    if not data:
        worksheet.append_row(HEADER)


    amazon_order_list = []
    for item in orders.json()['payload'].get("Orders"):
        amazon_order_list.append(
            AmazonOrder(
                order_id=item.get("AmazonOrderId", ''),
                purchase_date=item.get("PurchaseDate", ''),
                order_status=item.get("OrderStatus", ''),
                order_total=item.get("OrderTotal", {}).get("Amount", ""),
                payment_method=item.get("PaymentMethod", ''),
                marketplace_id=item.get("MarketplaceId", ''),
                shipment_service_level_category=item.get("ShipmentServiceLevelCategory", ''),
                order_type=item.get("OrderType", ''),
            )
        )

    order_list_of_lists = [list(asdict(row).values()) for row in amazon_order_list]
    last_row_number = len(worksheet.col_values(1)) + 1
    worksheet.insert_rows(order_list_of_lists, last_row_number)

    # for i in amazon_order_list:
    #     worksheet.append_row(list(asdict(i).values()))


