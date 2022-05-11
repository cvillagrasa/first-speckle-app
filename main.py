from speckle_custom import SpeckleWebApp
from my_token import token

### Create a local "my_token.py" file where you just store your token as a string in a variable named token:
### token = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
### Info to obtain your token from your speckle.xyz account at https://speckle.guide/dev/tokens.html

if __name__ == '__main__':
    app = SpeckleWebApp(token=token)
