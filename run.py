"""Start the Flyway development server.

PyCharm: right-click this file -> Run 'run'. Then open http://127.0.0.1:5000
"""
from flyway import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
