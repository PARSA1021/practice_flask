from datetime import datetime
import bisect

def calculate_age(birthdate):
    """
    Calculate the age given a birthdate.

    Args:
        birthdate (datetime): The birthdate of the user.

    Returns:
        int: The calculated age.
    """
    today = datetime.now()
    age = today.year - birthdate.year
    # Adjust for upcoming birthdays within the year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        age -= 1
    return age

def determine_age_group(age):
    """
    Determine the age group based on a given age.

    Args:
        age (int): The age of the user.

    Returns:
        str: The age group (e.g., "20s", "30s").
    """
    # Define age group boundaries and labels
    age_groups = [
        (0, "Teen"),
        (20, "20s"),
        (30, "30s"),
        (40, "40s"),
        (50, "50s"),
        (60, "60s"),
        (70, "70s"),
        (80, "80s"),
        (90, "90s"),
        (100, "100+")
    ]

    # Use bisect to find the appropriate age group
    index = bisect.bisect_right([ag[0] for ag in age_groups], age) - 1
    return age_groups[index][1]