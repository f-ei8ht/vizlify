from typing import Annotated

from fastapi import Depends, Request

from app.core.config import settings
from app.paypal import build_client
from app.paypal.client import PayPalClient


def get_paypal(request: Request) -> PayPalClient:
    """The process-wide client, built lazily when the lifespan did not run."""
    client = getattr(request.app.state, "paypal", None)
    if client is None:
        client = build_client(settings)
        request.app.state.paypal = client
    return client


PayPalDep = Annotated[PayPalClient, Depends(get_paypal)]
