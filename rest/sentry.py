import os

import sentry_sdk


def init_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT"),
        traces_sample_rate=0.0,
    )
