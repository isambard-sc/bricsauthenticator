# Set token and run
# export REAL_TOKEN={your token}
# python3 check_token.py

import json
import os

import jwt

real_jwt = os.getenv("REAL_JWT")
if not real_jwt:
    raise ValueError("REAL_JWT environment variable is not set!")

decoded_token = jwt.decode(real_jwt, options={"verify_signature": False})


def normalize_projects(decoded_token):
    projects = decoded_token.get("projects")
    if projects is None:
        return {}

    print(f"Projects claim type: {type(projects)}")

    if isinstance(projects, str):  # If projects is a JSON string, decode it
        try:
            decoded_projects = json.loads(projects)
            print("Decoded Projects (formatted):")
            print(json.dumps(decoded_projects, indent=4))
            return decoded_projects
        except (json.JSONDecodeError, TypeError):
            print(f"Invalid projects format: {projects}")
            return {}

    return projects  # If already a dict, return as is


normalized_projects = normalize_projects(decoded_token)
print("Final Parsed Projects:", json.dumps(normalized_projects, indent=4))
