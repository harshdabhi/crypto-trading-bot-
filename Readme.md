## Create an conda env 
cmd: conda create env -n bot python==3.10 -y

## Install all dependencies
cmd: pip install -r requirements.txt

## Upload API key and API secret 
upload file name: file_bitmex.json 
( can also set env variable if deployed on cloud )

## Run the final.py file

cmd: python final.py
