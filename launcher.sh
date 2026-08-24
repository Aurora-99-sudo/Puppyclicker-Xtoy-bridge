#!/bin/bash

cd "$(dirname "$0")"

source clicker-bridge/bin/activate

python app.py
