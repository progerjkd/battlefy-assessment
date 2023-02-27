from fastapi import FastAPI
import secrets
import validators
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from boto3.dynamodb.conditions import Key
import boto3
from mangum import Mangum

import schemas

app = FastAPI()

table_name = os.environ['TABLE']

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(table_name)

def key_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)


@app.post("/")
def create_url(request: schemas.URLBase):

    if not validators.url(request.url):
        raise HTTPException(status_code=400, detail="The provided URL is not valid")

    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    key = "".join(secrets.choice(chars) for _ in range(6))
    
    response = table.put_item(
        Item={
            'target_url': request.url,
            'key': key
        }
    )
    return {"shortlink": f"/{key}"}

@app.get("/{url_key}")
def redirect_to_url(url_key: str, request: Request):
    
    response = table.query(KeyConditionExpression=Key('key').eq(url_key))

    if len(response['Items']) == 0:
        key_not_found(request)
    else:
        target_url = response['Items'][0]['target_url']
        return RedirectResponse(target_url)


handler = Mangum(app)