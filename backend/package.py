from __future__ import print_function

import os
import base64


from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse
import json
from dotenv import load_dotenv
import httpx


from pydantic import BaseModel
import asyncio

from openai import OpenAI
from fastapi.responses import StreamingResponse
from http import client

import uuid
import time
import urllib.parse

# Create router instance
router = APIRouter()
