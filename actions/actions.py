from robocorp.actions import action
from faker import Faker
import random

fake = Faker()

@action
def search_crm(term: str) -> str:
    """
    Searches CRM system for hits on companies, deals and contacts on a specific term

    Args:
        term (str): Search term to be used. Example: "International Semiconductor Ltd."

    Returns:
        str: List of entities found in the CRM for the search term
    """

    options = [0, 1, 2, 3]
    probabilities = [0.5, 0.1667, 0.1667, 0.1667]
    how_many = random.choices(options, weights=probabilities, k=1)[0]

    if how_many == 0:
        return "No matches found"
    else: 
        response = f"For term <{term}> following matches were found:\n\n"

        for i in range(how_many):
            response += f"{fake.name} is a contact at a company {term}\n"    

        return response
