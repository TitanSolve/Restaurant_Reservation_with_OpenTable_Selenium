from config import logger
from reservation import make_reservation
from cancellation import cancel_reservation

if __name__ == '__main__':
    # Oxylabs Proxy Configuration (example values)
    OX_PROXY_HOST = "pr.oxylabs.io"
    OX_PROXY_PORT = 7777
    OX_PROXY_USERNAME = "customer-dined_uDNrH-cc-us"
    OX_PROXY_PASSWORD = "dPx_________1"
    PROXY_SCHEME = "http"
    BROWSER_URL = ""
    RESTAURANT_ID = "mikiya-wagyu-shabu-house-new-york-3"

    # Uncomment to test a reservation:
    result = make_reservation(
        date="2025-05-23",
        hour=15,
        minute=15,
        party_size="1",
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone_number="1234567890",
        special_requests="Window seat preferred",
        make_booking=True,
        restaurant_id=RESTAURANT_ID,
        browser_url=BROWSER_URL,
        proxy_host=OX_PROXY_HOST,
        proxy_port=OX_PROXY_PORT,
        proxy_username=OX_PROXY_USERNAME,
        proxy_password=OX_PROXY_PASSWORD,
        proxy_scheme=PROXY_SCHEME
    )
    logger.info("Reservation Result: %s", result)

    # Test cancellation
    # result = cancel_reservation(
    #     cancel_url="https://www.yelp.com/reservations/mikiya-wagyu-shabu-house-new-york-3/confirmed/9ff24e21-a4c336-45af-aca5-4c80fa4968de?f=c6HT44PKCaXqzN_BdgKPCw&checkout-success=1",
    #     browser_url="",
    #     proxy_host=None,
    #     proxy_port=None,
    #     proxy_username=None,
    #     proxy_password=None,
    #     proxy_scheme="http",
    # )
    # logger.info("Cancellation Result: %s", result)
