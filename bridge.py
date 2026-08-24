import asyncio
import json
import logging
import os
import random
import time

import aiohttp


# ============================================================
# Paths
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CONFIG_FILE = os.path.join(
    BASE_DIR,
    "config.json"
)


# ============================================================
# PuppyClicker
# ============================================================

PUPPYCLICKER_STREAM_URL = (
    "https://puppyclicker-api.boundfire.com/api/v2/stream"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger(
    "puppyclicker-xtoys"
)


# ============================================================
# Runtime configuration
# ============================================================

PUPPYCLICKER_API_KEY = ""
XTOYS_WEBHOOK_URL = ""

GAMEMODE = 1
COOLDOWN_SECONDS = 2.0

CATEGORIES = {
    "Tease": {
        "duration": 3.0
    },
    "Pleasure": {
        "duration": 5.0
    },
    "Punish": {
        "duration": 2.0
    }
}

KEYWORDS = {
    "Pleasure": [],
    "Punish": []
}

RANDOM_WEIGHTS = {
    "Tease": 1,
    "Pleasure": 1,
    "Punish": 1
}


# ============================================================
# Runtime state
# ============================================================

last_trigger_time = 0.0

active_category_task = None


# ============================================================
# Configuration
# ============================================================

def load_config():

    global PUPPYCLICKER_API_KEY
    global XTOYS_WEBHOOK_URL
    global GAMEMODE
    global COOLDOWN_SECONDS
    global CATEGORIES
    global KEYWORDS
    global RANDOM_WEIGHTS

    if not os.path.exists(CONFIG_FILE):

        raise RuntimeError(
            "config.json was not found.\n"
            "Open app.py and save your configuration first."
        )

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            config = json.load(file)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            f"config.json contains invalid JSON: {exc}"
        )

    PUPPYCLICKER_API_KEY = (
        str(
            config.get(
                "puppycliker_api_key",
                ""
            )
        )
        .strip()
    )

    webhook_id = (
        str(
            config.get(
                "xtoys_webhook_id",
                ""
            )
        )
        .strip()
    )

    if not PUPPYCLICKER_API_KEY:

        raise RuntimeError(
            "PuppyClicker API key is missing."
        )

    if not webhook_id:

        raise RuntimeError(
            "XToys webhook ID is missing."
        )

    XTOYS_WEBHOOK_URL = (
        "https://webhook.xtoys.app/"
        + webhook_id
    )

    try:

        GAMEMODE = int(
            config.get(
                "gamemode",
                1
            )
        )

    except (TypeError, ValueError):

        raise RuntimeError(
            "Gamemode must be 1, 2 or 3."
        )

    if GAMEMODE not in (1, 2, 3):

        raise RuntimeError(
            "Gamemode must be 1, 2 or 3."
        )

    try:

        COOLDOWN_SECONDS = float(
            config.get(
                "cooldown_seconds",
                2.0
            )
        )

    except (TypeError, ValueError):

        raise RuntimeError(
            "cooldown_seconds must be a number."
        )

    if COOLDOWN_SECONDS < 0:

        raise RuntimeError(
            "cooldown_seconds cannot be negative."
        )

    configured_categories = config.get(
        "categories",
        {}
    )

    for category in (
        "Tease",
        "Pleasure",
        "Punish"
    ):

        settings = (
            configured_categories.get(
                category,
                {}
            )
        )

        try:

            duration = float(
                settings.get(
                    "duration",
                    CATEGORIES[
                        category
                    ]["duration"]
                )
            )

        except (TypeError, ValueError):

            raise RuntimeError(
                f"{category} duration must be a number."
            )

        if duration < 0:

            raise RuntimeError(
                f"{category} duration cannot be negative."
            )

        CATEGORIES[
            category
        ]["duration"] = duration

    configured_keywords = config.get(
        "keywords",
        {}
    )

    for category in (
        "Pleasure",
        "Punish"
    ):

        values = configured_keywords.get(
            category,
            []
        )

        if not isinstance(
            values,
            list
        ):

            raise RuntimeError(
                f"{category} keywords must be a list."
            )

        KEYWORDS[
            category
        ] = [
            str(word).strip().lower()
            for word in values
            if str(word).strip()
        ]
    # --------------------------------------------------------
    # Random weights
    # --------------------------------------------------------

    configured_weights = config.get(
        "random_weights",
        {}
    )

    if not isinstance(
        configured_weights,
        dict
    ):

        raise RuntimeError(
            "random_weights must be an object."
        )

    for category in (
        "Tease",
        "Pleasure",
        "Punish"
    ):

        try:

            weight = float(
                configured_weights.get(
                    category,
                    RANDOM_WEIGHTS[category]
                )
            )

        except (TypeError, ValueError):

            raise RuntimeError(
                f"{category} random weight "
                "must be a number."
            )

        if weight < 0:

            raise RuntimeError(
                f"{category} random weight "
                "cannot be negative."
            )

        RANDOM_WEIGHTS[
            category
        ] = weight

    if sum(
        RANDOM_WEIGHTS.values()
    ) <= 0:

        raise RuntimeError(
            "At least one random weight "
            "must be greater than zero."
        )

# ============================================================
# XToys
# ============================================================

async def send_xtoys_action(
    session,
    action
):
    payload = {
        "action": action
    }

    log.info(
        "XToys -> %s",
        action
    )

    try:

        async with session.post(
            XTOYS_WEBHOOK_URL,
            json=payload,
            ssl=False,
            timeout=aiohttp.ClientTimeout(
                total=10
            )
        ) as response:

            response_text = (
                await response.text()
            )

            if response.status >= 400:

                log.error(
                    "XToys returned HTTP %s: %s",
                    response.status,
                    response_text
                )

                return False

            log.info(
                "XToys response: HTTP %s",
                response.status
            )

            if response_text:

                log.debug(
                    "XToys response body: %s",
                    response_text
                )

            return True

    except asyncio.CancelledError:

        raise

    except Exception:

        log.exception(
            "Failed to send XToys action."
        )

        return False


# ============================================================
# Message classification
# ============================================================

def classify_message(body):
    """
    Convert PuppyClicker message text into a category.

    Priority:
        Punish
        Pleasure
        Tease
    """

    text = (
        str(body)
        .strip()
        .lower()
    )

    if not text:

        return "Tease"

    # Check Punish first.
    for keyword in KEYWORDS["Punish"]:

        if keyword in text:

            return "Punish"

    # Then Pleasure.
    for keyword in KEYWORDS["Pleasure"]:

        if keyword in text:

            return "Pleasure"

    # Everything else becomes Tease.
    return "Tease"


# ============================================================
# Category selection
# ============================================================

def select_category(
    alert
):
    """
    Select Tease, Pleasure or Punish
    according to the configured gamemode.

    Mode 1:
        Always Tease.

    Mode 2:
        Classify the message.

    Mode 3:
        Weighted random selection.
    """

    # --------------------------------------------------------
    # Mode 1
    #
    # Everything is Tease.
    # --------------------------------------------------------

    if GAMEMODE == 1:

        return "Tease"

    # --------------------------------------------------------
    # Mode 2
    #
    # Message classification.
    # --------------------------------------------------------

    if GAMEMODE == 2:

        body = alert.get(
            "body",
            ""
        )

        category = classify_message(
            body
        )

        log.info(
            "Message classification: %s",
            category
        )

        return category

    # --------------------------------------------------------
    # Mode 3
    #
    # Weighted random category.
    # --------------------------------------------------------

    if GAMEMODE == 3:

        category = random.choices(
            population=[
                "Tease",
                "Pleasure",
                "Punish"
            ],
            weights=[
                RANDOM_WEIGHTS["Tease"],
                RANDOM_WEIGHTS["Pleasure"],
                RANDOM_WEIGHTS["Punish"]
            ],
            k=1
        )[0]

        log.info(
            "Random selection: %s | weights=%s",
            category,
            RANDOM_WEIGHTS
        )

        return category

    # --------------------------------------------------------
    # Invalid mode
    # --------------------------------------------------------

    raise RuntimeError(
        f"Invalid gamemode: {GAMEMODE}"
    )


# ============================================================
# Run a category
# ============================================================

async def run_category(
    session,
    category
):
    """
    Send:
        Tease
        Pleasure
        Punish

    Wait for the configured duration.

    Then send:
        Tease_off
        Pleasure_off
        Punish_off
    """

    if category not in CATEGORIES:

        log.error(
            "Unknown category: %s",
            category
        )

        return

    duration = CATEGORIES[
        category
    ]["duration"]

    off_action = (
        category
        + "_off"
    )

    log.info(
        "Starting %s for %.2f seconds.",
        category,
        duration
    )

    # --------------------------------------------------------
    # ON
    # --------------------------------------------------------

    success = await send_xtoys_action(
        session,
        category
    )

    if not success:

        log.error(
            "%s start command failed.",
            category
        )

        return

    try:

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        if duration > 0:

            await asyncio.sleep(
                duration
            )

    except asyncio.CancelledError:

        # If the category is cancelled, still attempt
        # to send the OFF command before propagating
        # cancellation.

        log.info(
            "%s task cancelled; sending OFF.",
            category
        )

        await send_xtoys_action(
            session,
            off_action
        )

        raise

    # --------------------------------------------------------
    # OFF
    # --------------------------------------------------------

    success = await send_xtoys_action(
        session,
        off_action
    )

    if success:

        log.info(
            "%s finished.",
            category
        )

    else:

        log.error(
            "%s OFF command failed.",
            category
        )


# ============================================================
# Trigger handling
# ============================================================

async def handle_alert(
    session,
    alert
):
    global last_trigger_time
    global active_category_task

    kind = alert.get(
        "kind"
    )

    body = alert.get(
        "body",
        ""
    )

    sender = alert.get(
        "senderUsername",
        "unknown"
    )

    log.info(
        "PuppyClicker alert | kind=%s | "
        "sender=%s | body=%s",
        kind,
        sender,
        body
    )

    # --------------------------------------------------------
    # We only care about clicks and messages.
    #
    # The API can also provide:
    #   comment
    #   reaction_emoji
    #   reaction_button
    #
    # These are deliberately ignored for now.
    # --------------------------------------------------------

    if kind not in (
        "click",
        "message"
    ):

        return

    # --------------------------------------------------------
    # DND suppression
    # --------------------------------------------------------

    if alert.get(
        "dndSuppressed",
        False
    ):

        log.info(
            "Ignoring DND-suppressed event."
        )

        return

    # --------------------------------------------------------
    # Don't overlap categories.
    # --------------------------------------------------------

    if (
        active_category_task is not None
        and not active_category_task.done()
    ):

        log.info(
            "Ignoring event because %s is "
            "already running.",
            "a category"
        )

        return

    # --------------------------------------------------------
    # Cooldown
    # --------------------------------------------------------

    now = time.monotonic()

    elapsed = (
        now - last_trigger_time
    )

    if elapsed < COOLDOWN_SECONDS:

        remaining = (
            COOLDOWN_SECONDS
            - elapsed
        )

        log.info(
            "Ignoring event due to cooldown "
            "(%.2f seconds remaining).",
            remaining
        )

        return

    # --------------------------------------------------------
    # Select category
    # --------------------------------------------------------

    category = select_category(
        alert
    )

    log.info(
        "Selected category: %s",
        category
    )

    # Mark this before starting the task.
    last_trigger_time = now

    active_category_task = (
        asyncio.create_task(
            run_category(
                session,
                category
            )
        )
    )


# ============================================================
# SSE parsing
# ============================================================

async def process_sse_stream(
    response,
    session
):
    """
    Process PuppyClicker's Server-Sent Events stream.
    """

    event_type = None
    data_lines = []

    async for raw_line in (
        response.content
    ):

        line = (
            raw_line
            .decode(
                "utf-8",
                errors="replace"
            )
            .rstrip(
                "\r\n"
            )
        )

        # ----------------------------------------------------
        # Empty line = end of SSE event
        # ----------------------------------------------------

        if line == "":

            if data_lines:

                data = "\n".join(
                    data_lines
                )

                try:

                    payload = json.loads(
                        data
                    )

                except json.JSONDecodeError:

                    log.warning(
                        "Invalid SSE JSON: %s",
                        data
                    )

                    event_type = None
                    data_lines = []

                    continue

                # ------------------------------------------------
                # ready event
                # ------------------------------------------------

                if event_type == "ready":

                    log.info(
                        "PuppyClicker stream ready."
                    )

                # ------------------------------------------------
                # alert event
                # ------------------------------------------------

                elif event_type == "alert":

                    await handle_alert(
                        session,
                        payload
                    )

            event_type = None
            data_lines = []

            continue

        # ----------------------------------------------------
        # Comments / keepalive
        # ----------------------------------------------------

        if line.startswith(":"):

            continue

        # ----------------------------------------------------
        # Event name
        # ----------------------------------------------------

        if line.startswith(
            "event:"
        ):

            event_type = (
                line[
                    len("event:")
                :].strip()
            )

        # ----------------------------------------------------
        # Event data
        # ----------------------------------------------------

        elif line.startswith(
            "data:"
        ):

            data_lines.append(
                line[
                    len("data:")
                :].lstrip()
            )


# ============================================================
# PuppyClicker connection
# ============================================================

async def listen_to_puppyclicker():

    headers = {
        "Authorization": (
            "Bearer "
            + PUPPYCLICKER_API_KEY
        ),
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
    }

    timeout = aiohttp.ClientTimeout(
        total=None,
        connect=15,
        sock_read=None
    )

    reconnect_delay = 3

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        while True:

            try:

                log.info(
                    "Connecting to PuppyClicker..."
                )

                async with session.get(
                    PUPPYCLICKER_STREAM_URL,
                    headers=headers
                ) as response:

                    # ------------------------------------------------
                    # Connection failure
                    # ------------------------------------------------

                    if response.status != 200:

                        body = (
                            await response.text()
                        )

                        raise RuntimeError(
                            "PuppyClicker returned "
                            f"HTTP {response.status}: "
                            f"{body[:500]}"
                        )

                    # ------------------------------------------------
                    # Connected
                    # ------------------------------------------------

                    log.info(
                        "Connected to PuppyClicker."
                    )

                    reconnect_delay = 3

                    await process_sse_stream(
                        response,
                        session
                    )

                    log.warning(
                        "PuppyClicker stream ended."
                    )

            except asyncio.CancelledError:

                raise

            except Exception as exc:

                log.warning(
                    "PuppyClicker connection lost: %s",
                    exc
                )

                log.info(
                    "Reconnecting in %s seconds...",
                    reconnect_delay
                )

                await asyncio.sleep(
                    reconnect_delay
                )

                reconnect_delay = min(
                    reconnect_delay * 2,
                    60
                )


# ============================================================
# Main
# ============================================================

async def main():

    load_config()

    log.info(
        "========================================"
    )

    log.info(
        "PuppyClicker -> XToys bridge"
    )

    log.info(
        "========================================"
    )

    log.info(
        "Gamemode: %d",
        GAMEMODE
    )

    log.info(
        "Cooldown: %.2f seconds",
        COOLDOWN_SECONDS
    )

    for category, settings in (
        CATEGORIES.items()
    ):

        log.info(
            "%s duration: %.2f seconds",
            category,
            settings["duration"]
        )

    log.info(
        "Pleasure keywords: %s",
        ", ".join(
            KEYWORDS["Pleasure"]
        )
    )

    log.info(
        "Punish keywords: %s",
        ", ".join(
            KEYWORDS["Punish"]
        )
    )

    await listen_to_puppyclicker()


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        log.info(
            "Bridge stopped."
        )