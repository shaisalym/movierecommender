
# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     app.run(debug=True)


import os
from app import create_app

# Create the app using the factory function
app = create_app()

if __name__ == '__main__':
    # Use environment variables for production (host = 0.0.0.0, port = $PORT)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
