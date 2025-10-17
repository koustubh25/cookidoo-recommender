#!/usr/bin/env python3
"""Startup script for the recipe recommendation chatbot."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbot.interface import main

if __name__ == "__main__":
    main()
