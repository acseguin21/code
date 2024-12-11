from urllib.parse import quote

# Prompt the user to enter the token
token = input("Enter the token to be URL-encoded: ")

# URL-encode the token
encoded_token = quote(token)

print("Encoded Token:", encoded_token)