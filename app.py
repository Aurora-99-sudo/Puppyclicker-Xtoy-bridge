import asyncio
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

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

BRIDGE_FILE = os.path.join(
    BASE_DIR,
    "bridge.py"
)


# ============================================================
# Defaults
# ============================================================

DEFAULT_CONFIG = {
    "puppycliker_api_key": "",
    "xtoys_webhook_id": "",

    "gamemode": 1,

    "cooldown_seconds": 2.0,

    "categories": {
        "Tease": {
            "duration": 3.0
        },

        "Pleasure": {
            "duration": 5.0
        },

        "Punish": {
            "duration": 2.0
        }
    },

    "keywords": {
        "Pleasure": [
            "good",
            "good puppy",
            "good boy",
            "good girl",
            "well done",
            "proud",
            "praise",
            "pleasure"
        ],

        "Punish": [
            "bad",
            "bad puppy",
            "bad boy",
            "bad girl",
            "naughty",
            "punish",
            "punishment",
            "degradation",
            "degrade",
            "pathetic"
        ]
    },

    "random_weights": {
        "Tease": 5,
        "Pleasure": 3,
        "Punish": 2
    }
}


# ============================================================
# Configuration helpers
# ============================================================

def deep_copy_default():

    return json.loads(
        json.dumps(
            DEFAULT_CONFIG
        )
    )


def load_config():

    if not os.path.exists(
        CONFIG_FILE
    ):

        return deep_copy_default()

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            loaded = json.load(file)

    except Exception:

        return deep_copy_default()

    config = deep_copy_default()

    if isinstance(
        loaded,
        dict
    ):

        config.update(
            loaded
        )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    if isinstance(
        loaded.get("categories"),
        dict
    ):

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            values = loaded[
                "categories"
            ].get(
                category
            )

            if isinstance(
                values,
                dict
            ):

                config[
                    "categories"
                ][category].update(
                    values
                )

    # --------------------------------------------------------
    # Keywords
    # --------------------------------------------------------

    if isinstance(
        loaded.get("keywords"),
        dict
    ):

        for category in (
            "Pleasure",
            "Punish"
        ):

            values = loaded[
                "keywords"
            ].get(
                category
            )

            if isinstance(
                values,
                list
            ):

                config[
                    "keywords"
                ][category] = values

    # --------------------------------------------------------
    # Random weights
    # --------------------------------------------------------

    if isinstance(
        loaded.get("random_weights"),
        dict
    ):

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            if category in loaded[
                "random_weights"
            ]:

                config[
                    "random_weights"
                ][category] = loaded[
                    "random_weights"
                ][category]

    return config


def save_config(config):

    temporary_file = (
        CONFIG_FILE
        + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            config,
            file,
            indent=4
        )

    os.replace(
        temporary_file,
        CONFIG_FILE
    )


# ============================================================
# Main application
# ============================================================

class App:

    def __init__(
        self,
        root
    ):

        self.root = root

        self.root.title(
            "PuppyClicker → XToys"
        )

        # Fixed-size window.
        self.root.geometry(
            "760x1240"
        )

        self.root.resizable(
            False,
            False
        )

        self.config = load_config()

        self.bridge_process = None

        self.create_variables()
        self.create_ui()
        self.load_into_ui()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        self.update_status()

    # ========================================================
    # Variables
    # ========================================================

    def create_variables(self):

        self.api_key = tk.StringVar()

        self.webhook_id = tk.StringVar()

        self.show_api_key = tk.BooleanVar(
            value=False
        )

        self.gamemode = tk.IntVar(
            value=1
        )

        self.cooldown = tk.StringVar(
            value="2.0"
        )

        self.status = tk.StringVar(
            value="Bridge stopped"
        )

        # ----------------------------------------------------
        # Durations
        # ----------------------------------------------------

        self.duration_vars = {}

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            self.duration_vars[
                category
            ] = tk.StringVar()

        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        self.pleasure_keywords = (
            tk.StringVar()
        )

        self.punish_keywords = (
            tk.StringVar()
        )

        # ----------------------------------------------------
        # Random weights
        # ----------------------------------------------------

        self.random_weight_vars = {}

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            self.random_weight_vars[
                category
            ] = tk.StringVar()

        self.random_percentage_vars = {}

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            self.random_percentage_vars[
                category
            ] = tk.StringVar(
                value="0.0%"
            )

    # ========================================================
    # UI
    # ========================================================

    def create_ui(self):

        container = ttk.Frame(
            self.root,
            padding=16
        )

        container.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        ttk.Label(
            container,
            text="PuppyClicker → XToys",
            font=(
                "TkDefaultFont",
                20,
                "bold"
            )
        ).pack(
            anchor="w"
        )

        ttk.Label(
            container,
            text=(
                "Connect PuppyClicker events to XToys "
                "categories."
            )
        ).pack(
            anchor="w",
            pady=(2, 15)
        )

        self.create_connection_section(
            container
        )

        self.create_gamemode_section(
            container
        )

        self.create_category_section(
            container
        )

        self.create_random_section(
            container
        )

        self.create_keyword_section(
            container
        )

        self.create_cooldown_section(
            container
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status_frame = ttk.Frame(
            container
        )

        status_frame.pack(
            fill="x",
            pady=(12, 8)
        )

        ttk.Label(
            status_frame,
            text="Status:"
        ).pack(
            side="left"
        )

        ttk.Label(
            status_frame,
            textvariable=self.status
        ).pack(
            side="left",
            padx=(6, 0)
        )

        self.create_button_section(
            container
        )

    # ========================================================
    # Connection
    # ========================================================

    def create_connection_section(
        self,
        parent
    ):

        frame = ttk.LabelFrame(
            parent,
            text="Connection",
            padding=12
        )

        frame.pack(
            fill="x",
            pady=(0, 10)
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            frame,
            text="PuppyClicker API key:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=5
        )

        self.api_entry = ttk.Entry(
            frame,
            textvariable=self.api_key,
            show="*"
        )

        self.api_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=10
        )

        ttk.Checkbutton(
            frame,
            text="Show",
            variable=self.show_api_key,
            command=self.toggle_api_key
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )

        ttk.Label(
            frame,
            text="XToys webhook ID:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=5
        )

        ttk.Entry(
            frame,
            textvariable=self.webhook_id
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=10
        )

        ttk.Label(
            frame,
            text="Private webhook ID"
        ).grid(
            row=1,
            column=2,
            sticky="w"
        )

    # ========================================================
    # Gamemode
    # ========================================================

    def create_gamemode_section(
        self,
        parent
    ):

        frame = ttk.LabelFrame(
            parent,
            text="Gamemode",
            padding=12
        )

        frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Radiobutton(
            frame,
            text="1 — Tease only",
            variable=self.gamemode,
            value=1
        ).pack(
            anchor="w",
            pady=2
        )

        ttk.Label(
            frame,
            text=(
                "Every accepted event triggers Tease."
            )
        ).pack(
            anchor="w",
            padx=(25, 0),
            pady=(0, 5)
        )

        ttk.Radiobutton(
            frame,
            text="2 — Message based",
            variable=self.gamemode,
            value=2
        ).pack(
            anchor="w",
            pady=2
        )

        ttk.Label(
            frame,
            text=(
                "Messages are classified using the "
                "keywords below."
            )
        ).pack(
            anchor="w",
            padx=(25, 0),
            pady=(0, 5)
        )

        ttk.Radiobutton(
            frame,
            text="3 — Random",
            variable=self.gamemode,
            value=3
        ).pack(
            anchor="w",
            pady=2
        )

        ttk.Label(
            frame,
            text=(
                "Randomly selects a category using the "
                "weights configured below."
            )
        ).pack(
            anchor="w",
            padx=(25, 0)
        )

    # ========================================================
    # Category durations
    # ========================================================

    def create_category_section(
        self,
        parent
    ):

        frame = ttk.LabelFrame(
            parent,
            text="Category durations",
            padding=12
        )

        frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            frame,
            text="Category",
            font=(
                "TkDefaultFont",
                9,
                "bold"
            )
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=(0, 8)
        )

        ttk.Label(
            frame,
            text="Duration",
            font=(
                "TkDefaultFont",
                9,
                "bold"
            )
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=(0, 8)
        )

        row = 1

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            ttk.Label(
                frame,
                text=category
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=5,
                pady=4
            )

            ttk.Entry(
                frame,
                textvariable=(
                    self.duration_vars[
                        category
                    ]
                ),
                width=12
            ).grid(
                row=row,
                column=1,
                sticky="w",
                padx=5,
                pady=4
            )

            ttk.Label(
                frame,
                text="seconds"
            ).grid(
                row=row,
                column=2,
                sticky="w",
                padx=5
            )

            row += 1

        ttk.Label(
            frame,
            text=(
                "The bridge sends the category action, "
                "waits for the duration, then sends "
                "<category>_off."
            )
        ).grid(
            row=row,
            column=0,
            columnspan=3,
            sticky="w",
            padx=5,
            pady=(8, 0)
        )

    # ========================================================
    # Random weights
    # ========================================================

    def create_random_section(
        self,
        parent
    ):

        frame = ttk.LabelFrame(
            parent,
            text="Random mode weights",
            padding=12
        )

        frame.pack(
            fill="x",
            pady=(0, 10)
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            frame,
            text="Category",
            font=(
                "TkDefaultFont",
                9,
                "bold"
            )
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=(0, 8)
        )

        ttk.Label(
            frame,
            text="Weight",
            font=(
                "TkDefaultFont",
                9,
                "bold"
            )
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=5,
            pady=(0, 8)
        )

        ttk.Label(
            frame,
            text="Chance",
            font=(
                "TkDefaultFont",
                9,
                "bold"
            )
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=15,
            pady=(0, 8)
        )

        row = 1

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            ttk.Label(
                frame,
                text=category
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=5,
                pady=4
            )

            entry = ttk.Entry(
                frame,
                textvariable=(
                    self.random_weight_vars[
                        category
                    ]
                ),
                width=12
            )

            entry.grid(
                row=row,
                column=1,
                sticky="w",
                padx=5,
                pady=4
            )

            entry.bind(
                "<KeyRelease>",
                lambda event:
                    self.update_random_percentages()
            )

            ttk.Label(
                frame,
                textvariable=(
                    self.random_percentage_vars[
                        category
                    ]
                ),
                width=10
            ).grid(
                row=row,
                column=2,
                sticky="w",
                padx=15
            )

            row += 1

        self.random_total_label = ttk.Label(
            frame,
            text="Total weight: 0"
        )

        self.random_total_label.grid(
            row=row,
            column=0,
            columnspan=3,
            sticky="w",
            padx=5,
            pady=(8, 0)
        )

        ttk.Label(
            frame,
            text=(
                "Weights do not need to add up to 100. "
                "For example, 5 / 3 / 2 gives "
                "50% / 30% / 20%."
            )
        ).grid(
            row=row + 1,
            column=0,
            columnspan=3,
            sticky="w",
            padx=5,
            pady=(5, 0)
        )

    # ========================================================
    # Keywords
    # ========================================================

    def create_keyword_section(
        self,
        parent
    ):

        frame = ttk.LabelFrame(
            parent,
            text="Message classification",
            padding=12
        )

        frame.pack(
            fill="x",
            pady=(0, 10)
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            frame,
            text="Pleasure keywords:"
        ).grid(
            row=0,
            column=0,
            sticky="nw",
            padx=5,
            pady=5
        )

        ttk.Entry(
            frame,
            textvariable=(
                self.pleasure_keywords
            )
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=8,
            pady=5
        )

        ttk.Label(
            frame,
            text="comma separated"
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )

        ttk.Label(
            frame,
            text="Punish keywords:"
        ).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=5,
            pady=5
        )

        ttk.Entry(
            frame,
            textvariable=(
                self.punish_keywords
            )
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=5
        )

        ttk.Label(
            frame,
            text="comma separated"
        ).grid(
            row=1,
            column=2,
            sticky="w"
        )

        ttk.Label(
            frame,
            text=(
                "Punish is checked first, then Pleasure. "
                "Anything else becomes Tease."
            )
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            padx=5,
            pady=(8, 0)
        )

    # ========================================================
    # Cooldown
    # ========================================================

    def create_cooldown_section(
        self,
        parent
    ):

        frame = ttk.Frame(
            parent
        )

        frame.pack(
            fill="x"
        )

        ttk.Label(
            frame,
            text="Click cooldown:"
        ).pack(
            side="left"
        )

        ttk.Entry(
            frame,
            textvariable=self.cooldown,
            width=10
        ).pack(
            side="left",
            padx=7
        )

        ttk.Label(
            frame,
            text="seconds"
        ).pack(
            side="left"
        )

    # ========================================================
    # Buttons
    # ========================================================

    def create_button_section(
        self,
        parent
    ):

        test_frame = ttk.LabelFrame(
            parent,
            text="XToys tests",
            padding=10
        )

        test_frame.pack(
            fill="x",
            pady=(8, 10)
        )

        ttk.Button(
            test_frame,
            text="Test Tease",
            command=lambda:
                self.test_category(
                    "Tease"
                )
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            test_frame,
            text="Test Pleasure",
            command=lambda:
                self.test_category(
                    "Pleasure"
                )
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            test_frame,
            text="Test Punish",
            command=lambda:
                self.test_category(
                    "Punish"
                )
        ).pack(
            side="left",
            padx=4
        )

        button_frame = ttk.Frame(
            parent
        )

        button_frame.pack(
            fill="x"
        )

        ttk.Button(
            button_frame,
            text="Save Configuration",
            command=self.save
        ).pack(
            side="left"
        )

        ttk.Button(
            button_frame,
            text="Stop Bridge",
            command=self.stop_bridge
        ).pack(
            side="right"
        )

        ttk.Button(
            button_frame,
            text="Start Bridge",
            command=self.start_bridge
        ).pack(
            side="right",
            padx=6
        )

    # ========================================================
    # Load UI
    # ========================================================

    def load_into_ui(self):

        self.api_key.set(
            self.config.get(
                "puppycliker_api_key",
                ""
            )
        )

        self.webhook_id.set(
            self.config.get(
                "xtoys_webhook_id",
                ""
            )
        )

        try:

            self.gamemode.set(
                int(
                    self.config.get(
                        "gamemode",
                        1
                    )
                )
            )

        except (
            TypeError,
            ValueError
        ):

            self.gamemode.set(
                1
            )

        self.cooldown.set(
            str(
                self.config.get(
                    "cooldown_seconds",
                    2.0
                )
            )
        )

        # ----------------------------------------------------
        # Durations
        # ----------------------------------------------------

        categories = self.config.get(
            "categories",
            {}
        )

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            duration = categories.get(
                category,
                {}
            ).get(
                "duration",
                DEFAULT_CONFIG[
                    "categories"
                ][category]["duration"]
            )

            self.duration_vars[
                category
            ].set(
                str(duration)
            )

        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        keywords = self.config.get(
            "keywords",
            {}
        )

        self.pleasure_keywords.set(
            ", ".join(
                str(x)
                for x in keywords.get(
                    "Pleasure",
                    []
                )
            )
        )

        self.punish_keywords.set(
            ", ".join(
                str(x)
                for x in keywords.get(
                    "Punish",
                    []
                )
            )
        )

        # ----------------------------------------------------
        # Random weights
        # ----------------------------------------------------

        weights = self.config.get(
            "random_weights",
            {}
        )

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            value = weights.get(
                category,
                DEFAULT_CONFIG[
                    "random_weights"
                ][category]
            )

            self.random_weight_vars[
                category
            ].set(
                str(value)
            )

        self.update_random_percentages()

    # ========================================================
    # Random percentage calculation
    # ========================================================

    def update_random_percentages(
        self
    ):

        weights = {}

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            try:

                value = float(
                    self.random_weight_vars[
                        category
                    ].get()
                )

                if value < 0:

                    value = 0

            except ValueError:

                value = 0

            weights[
                category
            ] = value

        total = sum(
            weights.values()
        )

        self.random_total_label.configure(
            text=(
                f"Total weight: {total:g}"
            )
        )

        if total <= 0:

            for category in (
                "Tease",
                "Pleasure",
                "Punish"
            ):

                self.random_percentage_vars[
                    category
                ].set(
                    "0.0%"
                )

            return

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            percentage = (
                weights[
                    category
                ]
                / total
                * 100
            )

            self.random_percentage_vars[
                category
            ].set(
                f"{percentage:.1f}%"
            )

    # ========================================================
    # Collect config
    # ========================================================

    def collect_config(self):

        api_key = (
            self.api_key
            .get()
            .strip()
        )

        webhook_id = (
            self.webhook_id
            .get()
            .strip()
        )

        if not api_key:

            raise ValueError(
                "PuppyClicker API key is required."
            )

        if not webhook_id:

            raise ValueError(
                "XToys webhook ID is required."
            )

        # ----------------------------------------------------
        # Gamemode
        # ----------------------------------------------------

        gamemode = self.gamemode.get()

        if gamemode not in (
            1,
            2,
            3
        ):

            raise ValueError(
                "Gamemode must be 1, 2 or 3."
            )

        # ----------------------------------------------------
        # Cooldown
        # ----------------------------------------------------

        try:

            cooldown = float(
                self.cooldown.get()
            )

        except ValueError:

            raise ValueError(
                "Cooldown must be a number."
            )

        if cooldown < 0:

            raise ValueError(
                "Cooldown cannot be negative."
            )

        # ----------------------------------------------------
        # Durations
        # ----------------------------------------------------

        categories = {}

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            try:

                duration = float(
                    self.duration_vars[
                        category
                    ].get()
                )

            except ValueError:

                raise ValueError(
                    f"{category} duration "
                    f"must be a number."
                )

            if duration < 0:

                raise ValueError(
                    f"{category} duration "
                    f"cannot be negative."
                )

            categories[
                category
            ] = {
                "duration": duration
            }

        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        pleasure = self.parse_keywords(
            self.pleasure_keywords.get()
        )

        punish = self.parse_keywords(
            self.punish_keywords.get()
        )

        # ----------------------------------------------------
        # Random weights
        # ----------------------------------------------------

        random_weights = {}

        total_weight = 0

        for category in (
            "Tease",
            "Pleasure",
            "Punish"
        ):

            try:

                weight = float(
                    self.random_weight_vars[
                        category
                    ].get()
                )

            except ValueError:

                raise ValueError(
                    f"{category} random weight "
                    f"must be a number."
                )

            if weight < 0:

                raise ValueError(
                    f"{category} random weight "
                    f"cannot be negative."
                )

            # Whole numbers are cleaner in config.json.
            if weight.is_integer():

                weight = int(weight)

            random_weights[
                category
            ] = weight

            total_weight += weight

        if total_weight <= 0:

            raise ValueError(
                "At least one random weight "
                "must be greater than zero."
            )

        return {
            "puppycliker_api_key": api_key,

            "xtoys_webhook_id": webhook_id,

            "gamemode": gamemode,

            "cooldown_seconds": cooldown,

            "categories": categories,

            "keywords": {
                "Pleasure": pleasure,
                "Punish": punish
            },

            "random_weights": random_weights
        }

    # ========================================================
    # Keyword parser
    # ========================================================

    @staticmethod
    def parse_keywords(
        text
    ):

        result = []

        for item in text.split(","):

            item = item.strip()

            if item:

                result.append(
                    item
                )

        return result

    # ========================================================
    # Save
    # ========================================================

    def save(self):

        try:

            config = (
                self.collect_config()
            )

            save_config(
                config
            )

            self.config = config

            self.status.set(
                "Configuration saved"
            )

            messagebox.showinfo(
                "Saved",
                "Configuration saved successfully."
            )

        except Exception as exc:

            messagebox.showerror(
                "Save failed",
                str(exc)
            )

    # ========================================================
    # API key visibility
    # ========================================================

    def toggle_api_key(self):

        if self.show_api_key.get():

            self.api_entry.configure(
                show=""
            )

        else:

            self.api_entry.configure(
                show="*"
            )

    # ========================================================
    # XToys test
    # ========================================================

    def test_category(
        self,
        category
    ):

        webhook_id = (
            self.webhook_id
            .get()
            .strip()
        )

        if not webhook_id:

            messagebox.showerror(
                "Missing webhook",
                "Enter the XToys webhook ID first."
            )

            return

        try:

            duration = float(
                self.duration_vars[
                    category
                ].get()
            )

        except ValueError:

            messagebox.showerror(
                "Invalid duration",
                f"{category} duration must be a number."
            )

            return

        if duration < 0:

            messagebox.showerror(
                "Invalid duration",
                f"{category} duration cannot be negative."
            )

            return

        url = (
            "https://webhook.xtoys.app/"
            + webhook_id
        )

        self.status.set(
            f"Testing {category}..."
        )

        thread = threading.Thread(
            target=self.test_worker,
            args=(
                url,
                category,
                duration
            ),
            daemon=True
        )

        thread.start()

    # ========================================================
    # XToys test worker
    # ========================================================

    def test_worker(
        self,
        url,
        category,
        duration
    ):

        async def run():

            timeout = aiohttp.ClientTimeout(
                total=10
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                # --------------------------------------------
                # ON
                # --------------------------------------------

                async with session.post(
                    url,
                    json={
                        "action": category
                    },
                    ssl=False
                ) as response:

                    response_text = (
                        await response.text()
                    )

                    if response.status >= 400:

                        raise RuntimeError(
                            f"XToys returned HTTP "
                            f"{response.status}: "
                            f"{response_text}"
                        )

                self.root.after(
                    0,
                    lambda: self.status.set(
                        f"Test: {category} ON"
                    )
                )

                # --------------------------------------------
                # Duration
                # --------------------------------------------

                await asyncio.sleep(
                    duration
                )

                # --------------------------------------------
                # OFF
                # --------------------------------------------

                off_action = (
                    category
                    + "_off"
                )

                async with session.post(
                    url,
                    json={
                        "action": off_action
                    },
                    ssl=False
                ) as response:

                    response_text = (
                        await response.text()
                    )

                    if response.status >= 400:

                        raise RuntimeError(
                            f"XToys returned HTTP "
                            f"{response.status}: "
                            f"{response_text}"
                        )

                self.root.after(
                    0,
                    lambda: self.status.set(
                        f"{category} test finished"
                    )
                )

        try:

            asyncio.run(
                run()
            )

        except Exception as exc:

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "XToys test failed",
                    str(exc)
                )
            )

            self.root.after(
                0,
                lambda: self.status.set(
                    "XToys test failed"
                )
            )

    # ========================================================
    # Start bridge
    # ========================================================

    def start_bridge(self):

        if (
            self.bridge_process
            and self.bridge_process.poll()
            is None
        ):

            self.status.set(
                "Bridge already running"
            )

            return

        try:

            config = (
                self.collect_config()
            )

            save_config(
                config
            )

            self.config = config

        except Exception as exc:

            messagebox.showerror(
                "Configuration error",
                str(exc)
            )

            return

        if not os.path.exists(
            BRIDGE_FILE
        ):

            messagebox.showerror(
                "Missing bridge.py",
                (
                    "bridge.py was not found in:\n\n"
                    + BASE_DIR
                )
            )

            return

        try:

            self.bridge_process = (
                subprocess.Popen(
                    [
                        sys.executable,
                        BRIDGE_FILE
                    ],
                    cwd=BASE_DIR
                )
            )

            self.status.set(
                "Bridge running"
            )

        except Exception as exc:

            self.bridge_process = None

            messagebox.showerror(
                "Could not start bridge",
                str(exc)
            )

    # ========================================================
    # Stop bridge
    # ========================================================

    def stop_bridge(self):

        process = (
            self.bridge_process
        )

        if process is None:

            self.status.set(
                "Bridge stopped"
            )

            return

        if process.poll() is None:

            try:

                process.terminate()

                process.wait(
                    timeout=3
                )

            except subprocess.TimeoutExpired:

                process.kill()

                try:

                    process.wait(
                        timeout=2
                    )

                except Exception:

                    pass

            except Exception:

                pass

        self.bridge_process = None

        self.status.set(
            "Bridge stopped"
        )

    # ========================================================
    # Status
    # ========================================================

    def update_status(self):

        process = (
            self.bridge_process
        )

        if process is not None:

            if process.poll() is not None:

                self.bridge_process = None

                self.status.set(
                    "Bridge stopped"
                )

        self.root.after(
            1000,
            self.update_status
        )

    # ========================================================
    # Close
    # ========================================================

    def close(self):

        self.stop_bridge()

        self.root.destroy()


# ============================================================
# Entry point
# ============================================================

def main():

    root = tk.Tk()

    App(
        root
    )

    root.mainloop()


if __name__ == "__main__":

    main()