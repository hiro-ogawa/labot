# Heorku

### herokuを登録

`heroku git:remote -a APP_NAME`

### 環境変数をherokuにプッシュする手順

```
heroku config:set \
OWNER_BOT_SECRET= \
OWNER_BOT_TOKEN= \
USER_BOT_SECRET= \
USER_BOT_TOKEN= \
USER_FRIEND_URL= \
BOT_ENDPOINT= \
PAY_ID= \
PAY_SECRET= \
PAY_ENDPOINT= \
OWNERLINEID=["xxx"] \
WASUREUSERLINEID=["yyy"] \
DEBUG=True
```

# LICENSE
MIT License
