from flask import Flask
from threading import Thread
app = Flask('')
@app.route('/')
def main(): 
    return "Running"

def run():
    app.run(host="0.0.0.0", port=8500)

def keep_alive():
    server = Thread(target=run)
    server.start()