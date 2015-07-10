from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app = Flask(__name__)
    # app.config['SERVER_NAME'] = "myapp.dev:5005"
    app.run(host='0.0.0.1'
        # port=app.config.get("PORT", 9000)
    )